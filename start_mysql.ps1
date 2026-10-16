$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$ini = Join-Path $root "mysql_local.ini"
$data = Join-Path $root "data\mysql"
$server = "C:\Program Files\MySQL\MySQL Server 26.7\bin\mysqld.exe"
if (-not (Test-Path -LiteralPath $server)) { throw "MySQL 26.7 server binary not found: $server" }
if (-not (Test-Path -LiteralPath (Join-Path $data "auto.cnf"))) { throw "EduAI MySQL is not initialized. Run install_mysql.ps1 once first." }
function Test-MySqlPort {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $pending = $client.BeginConnect("127.0.0.1", 3307, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(500)) { return $false }
        $client.EndConnect($pending)
        return $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

# Test the configured endpoint directly. Get-NetTCPConnection can omit a
# listener in some Windows environments even when mysqld is accepting clients.
if (Test-MySqlPort) {
    $matchingProcess = Get-Process -Name mysqld -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $server } |
        Select-Object -First 1
    if ($matchingProcess) {
        Write-Output "EduAI MySQL is already listening on 127.0.0.1:3307."
        exit 0
    }
    $listener = Get-NetTCPConnection -State Listen -LocalPort 3307 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        throw "Port 3307 is already in use by PID $($listener.OwningProcess). EduAI MySQL was not started."
    }
    throw "Port 3307 accepts connections, but its MySQL process could not be verified. EduAI MySQL was not started."
}
$pidFiles = Get-ChildItem -LiteralPath $data -Filter "*.pid" -File -ErrorAction SilentlyContinue
foreach ($pidFile in $pidFiles) {
    $ownerIdText = (Get-Content -LiteralPath $pidFile.FullName -Raw).Trim()
    if ($ownerIdText -notmatch '^\d+$') { throw "Cannot safely interpret the MySQL PID file: $($pidFile.FullName)" }
    $owner = Get-Process -Id ([int]$ownerIdText) -ErrorAction SilentlyContinue
    if ($owner -and $owner.ProcessName -ieq "mysqld") {
        $ownerPath = $owner.Path
        if (-not $ownerPath) {
            throw "PID file $($pidFile.Name) points to a live mysqld process (PID $ownerIdText), but its executable path could not be verified. Inspect that process before starting another server."
        }
        if ([System.IO.Path]::GetFullPath($ownerPath) -ieq [System.IO.Path]::GetFullPath($server)) {
            throw "PID file $($pidFile.Name) points to the MySQL 26.7 executable (PID $ownerIdText), but 127.0.0.1:3307 is not accepting connections. Review the MySQL logs under $data before starting another server."
        }
    }
    if ($owner) {
        Write-Warning "Removing stale MySQL PID file $($pidFile.Name): PID $ownerIdText belongs to '$($owner.ProcessName)', not the configured MySQL 26.7 server."
    }
    Remove-Item -LiteralPath $pidFile.FullName -Force
}
$stdout = Join-Path $data "mysql-startup.out.log"
$stderr = Join-Path $data "mysql-startup.err.log"
$proc = Start-Process -FilePath $server -ArgumentList @("--defaults-file=`"$ini`"", "--console") -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
$deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    $proc.Refresh()
    if ($proc.HasExited) { throw "MySQL exited with code $($proc.ExitCode). Review the server logs under $data." }
    if (Test-MySqlPort) {
        Write-Output "EduAI MySQL started on 127.0.0.1:3307 (PID $($proc.Id))."
        exit 0
    }
}
throw "MySQL did not start within 45 seconds. Review the server logs under $data."
