$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$server = "C:\Program Files\MySQL\MySQL Server 26.7\bin\mysqld.exe"
$client = "C:\Program Files\MySQL\MySQL Server 26.7\bin\mysql.exe"
$ini = Join-Path $root "mysql_local.ini"
$data = Join-Path $root "data\mysql"
$rootCnf = Join-Path $root ".mysql-root.cnf"
$controlCnf = Join-Path $root ".mysql-control.cnf"
$settingsPath = Join-Path $root ".streamlit\secrets.toml"
$bootstrapPath = Join-Path $root ".mysql-bootstrap.sql"

foreach ($required in @($server, $client, $ini, $rootCnf, $controlCnf, $settingsPath)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required MySQL setup file not found: $required" }
}
function Test-MySqlPort {
    $socket = New-Object System.Net.Sockets.TcpClient
    try {
        $pending = $socket.BeginConnect("127.0.0.1", 3307, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(500)) { return $false }
        $socket.EndConnect($pending)
        return $socket.Connected
    } catch {
        return $false
    } finally {
        $socket.Dispose()
    }
}
$portInUse = Test-MySqlPort
$pidFiles = Get-ChildItem -LiteralPath $data -Filter "*.pid" -File -ErrorAction SilentlyContinue
foreach ($pidFile in $pidFiles) {
    $ownerIdText = (Get-Content -LiteralPath $pidFile.FullName -Raw).Trim()
    if ($ownerIdText -notmatch '^\d+$') { throw "Cannot safely interpret the MySQL PID file: $($pidFile.FullName)" }
    $owner = Get-Process -Id ([int]$ownerIdText) -ErrorAction SilentlyContinue
    if ($owner) { throw "PID file $($pidFile.Name) points to a live process (PID $ownerIdText). Inspect it before starting another server." }
    Remove-Item -LiteralPath $pidFile.FullName -Force
}
New-Item -ItemType Directory -Force -Path $data | Out-Null
if ($portInUse) { throw "Port 3307 is already accepting connections. If this is EduAI MySQL, run start_mysql.ps1; otherwise stop the conflicting instance before installing." }

function Read-OptionValue([string]$Path, [string]$Key) {
    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match "^\s*$([regex]::Escape($Key))\s*=" } | Select-Object -First 1
    if (-not $line) { throw "Missing $Key in private option file $Path." }
    return (($line -split "=", 2)[1]).Trim().Trim('"').Trim("'")
}
function Read-MySqlSetting([string]$Key) {
    $inMysql = $false
    foreach ($line in Get-Content -LiteralPath $settingsPath) {
        if ($line -match '^\s*\[(.+)\]\s*$') { $inMysql = ($Matches[1] -eq 'mysql'); continue }
        if ($inMysql -and $line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.+?)\s*(?:#.*)?$") { return $Matches[1].Trim().Trim('"').Trim("'") }
    }
    throw "Missing mysql.$Key in $settingsPath."
}
$rootPassword = Read-OptionValue $rootCnf "password"
$controlPassword = Read-OptionValue $controlCnf "password"
$appPassword = Read-MySqlSetting "password"
if ($rootPassword -notmatch '^[0-9a-f]{64}$' -or $controlPassword -notmatch '^[0-9a-f]{64}$' -or $appPassword -notmatch '^[0-9a-f]{64}$') { throw "EduAI MySQL credentials are not in the expected generated format. Review the local configuration files without sharing their contents." }
if ((Read-MySqlSetting "host").Trim('"') -ne '127.0.0.1' -or (Read-MySqlSetting "port").Trim('"') -ne '3307' -or (Read-MySqlSetting "database").Trim('"') -ne 'eduai' -or (Read-MySqlSetting "user").Trim('"') -ne 'eduai_app') { throw "EduAI secrets.toml must point to 127.0.0.1:3307 / eduai / eduai_app for this local setup." }

if (-not (Test-Path -LiteralPath (Join-Path $data "auto.cnf"))) {
    if ((Get-ChildItem -LiteralPath $data -Force | Measure-Object).Count -gt 0) { throw "MySQL data folder is non-empty but uninitialized. Preserve it and inspect $data before proceeding." }
    & $server "--defaults-file=$ini" --initialize-insecure --console
    if ($LASTEXITCODE -ne 0) { throw "MySQL data directory initialization failed with exit code $LASTEXITCODE." }
}

$sql = @"
ALTER USER 'root'@'localhost' IDENTIFIED BY '$rootPassword';
CREATE DATABASE IF NOT EXISTS eduai CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'eduai_app'@'127.0.0.1' IDENTIFIED BY '$appPassword';
ALTER USER 'eduai_app'@'127.0.0.1' IDENTIFIED BY '$appPassword';
GRANT ALL PRIVILEGES ON eduai.* TO 'eduai_app'@'127.0.0.1';
CREATE USER IF NOT EXISTS 'eduai_control'@'127.0.0.1' IDENTIFIED BY '$controlPassword';
ALTER USER 'eduai_control'@'127.0.0.1' IDENTIFIED BY '$controlPassword';
GRANT SHUTDOWN ON *.* TO 'eduai_control'@'127.0.0.1';
"@
[System.IO.File]::WriteAllText($bootstrapPath, $sql, [System.Text.Encoding]::ASCII)
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $bootstrapPath /inheritance:r /grant:r "${identity}:(F)" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not restrict access to the temporary MySQL bootstrap file." }
$appClient = Join-Path $root ".mysql-app-check.cnf"
@"
[client]
protocol=TCP
host=127.0.0.1
port=3307
user=eduai_app
password=$appPassword
database=eduai
"@ | Set-Content -LiteralPath $appClient -Encoding ascii
& icacls $appClient /inheritance:r /grant:r "${identity}:(F)" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not restrict access to the temporary app credential file." }
$stdout = Join-Path $data "mysql-startup.out.log"
$stderr = Join-Path $data "mysql-startup.err.log"
$proc = Start-Process -FilePath $server -ArgumentList @("--defaults-file=`"$ini`"", "--init-file=`"$bootstrapPath`"", "--console") -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
$deadline = (Get-Date).AddSeconds(50)
$ready = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    $proc.Refresh()
    if ($proc.HasExited) { break }
    if (Test-MySqlPort) {
        try {
            $nativePreference = Get-Variable -Name PSNativeCommandUseErrorActionPreference -ValueOnly -ErrorAction SilentlyContinue
            $PSNativeCommandUseErrorActionPreference = $false
            $check = & $client "--defaults-file=$appClient" --connect-timeout=2 --batch --skip-column-names --execute="SELECT 1" 2>$null
            $checkExitCode = $LASTEXITCODE
        } catch {
            $checkExitCode = 1
            $check = @()
        } finally {
            if ($null -ne $nativePreference) { $PSNativeCommandUseErrorActionPreference = $nativePreference }
        }
        if ($checkExitCode -eq 0 -and (($check -join "").Trim() -eq "1")) { $ready = $true; break }
    }
}
if (-not $ready) { throw "EduAI MySQL did not finish setup. Review the server logs under $data; the temporary bootstrap file was kept for recovery." }
Remove-Item -LiteralPath $bootstrapPath -Force
Remove-Item -LiteralPath $appClient -Force
Write-Output "EduAI MySQL is initialized and running on 127.0.0.1:3307. Its database files are in $data. Run run_eduai7.ps1 to launch the app."





