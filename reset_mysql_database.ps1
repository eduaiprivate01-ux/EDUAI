param(
    [switch]$CreateAdmin
)

$ErrorActionPreference = "Stop"
$root = [System.IO.Path]::GetFullPath($PSScriptRoot)
$data = [System.IO.Path]::GetFullPath((Join-Path $root "data\mysql"))
$expectedData = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "data\mysql"))
$server = "C:\Program Files\MySQL\MySQL Server 26.7\bin\mysqld.exe"
$client = "C:\Program Files\MySQL\MySQL Server 26.7\bin\mysql.exe"
$ini = [System.IO.Path]::GetFullPath((Join-Path $root "mysql_local.ini"))
$rootCnf = Join-Path $root ".mysql-root.cnf"
$controlCnf = Join-Path $root ".mysql-control.cnf"
$settingsPath = Join-Path $root ".streamlit\secrets.toml"
$python = Join-Path (Split-Path -Parent $root) "model\.venv\Scripts\python.exe"
$installScript = Join-Path $root "install_mysql.ps1"
$adminScript = Join-Path $root "setup_admin.py"

if ($data -ne $expectedData -or (Split-Path -Parent $data) -ne [System.IO.Path]::GetFullPath((Join-Path $root "data"))) {
    throw "Refusing to reset an unexpected MySQL data path: $data"
}
foreach ($required in @($server, $client, $ini, $rootCnf, $controlCnf, $settingsPath, $python, $installScript)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required MySQL reset file not found: $required" }
}
if ($CreateAdmin -and -not (Test-Path -LiteralPath $adminScript)) {
    throw "The admin setup script was not found: $adminScript"
}

# Validate all connection credentials before deleting the current data folder.
function Read-OptionValue([string]$Path, [string]$Key) {
    $line = Get-Content -LiteralPath $Path | Where-Object {
        $_ -match "^\s*$([regex]::Escape($Key))\s*="
    } | Select-Object -First 1
    if (-not $line) { throw "Missing $Key in private option file $Path." }
    return (($line -split "=", 2)[1]).Trim().Trim('"').Trim("'")
}
function Read-MySqlSetting([string]$Key) {
    $inMysql = $false
    foreach ($line in Get-Content -LiteralPath $settingsPath) {
        if ($line -match '^\s*\[(.+)\]\s*$') {
            $inMysql = ($Matches[1] -eq 'mysql')
            continue
        }
        if ($inMysql -and $line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.+?)\s*(?:#.*)?$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    throw "Missing mysql.$Key in $settingsPath."
}
$rootPassword = Read-OptionValue $rootCnf "password"
$controlPassword = Read-OptionValue $controlCnf "password"
$appPassword = Read-MySqlSetting "password"
if ($rootPassword -notmatch '^[0-9a-f]{64}$' -or
    $controlPassword -notmatch '^[0-9a-f]{64}$' -or
    $appPassword -notmatch '^[0-9a-f]{64}$') {
    throw "MySQL credentials are not in the expected generated format. No database files were deleted."
}
if ((Read-MySqlSetting "host").Trim('"') -ne '127.0.0.1' -or
    (Read-MySqlSetting "port").Trim('"') -ne '3307' -or
    (Read-MySqlSetting "database").Trim('"') -ne 'eduai' -or
    (Read-MySqlSetting "user").Trim('"') -ne 'eduai_app') {
    throw "The app connection must target 127.0.0.1:3307 / eduai / eduai_app. No database files were deleted."
}

# Restrict reset to the project's dedicated SQL data directory. The separate
# uploaded-document and Chroma vector stores are not touched by this script.
$schemaDirectories = @(Get-ChildItem -LiteralPath $data -Directory -ErrorAction Stop |
    Where-Object { $_.Name -notin @("#innodb_redo", "#innodb_temp") } |
    Select-Object -ExpandProperty Name)
$allowedSchemas = @("eduai", "mysql", "performance_schema", "sys")
$unexpectedSchemas = @($schemaDirectories | Where-Object { $_ -notin $allowedSchemas })
if ($unexpectedSchemas.Count -gt 0) {
    throw "Refusing to delete MySQL data because unexpected database directories exist: $($unexpectedSchemas -join ', ')"
}
if (-not (Test-Path -LiteralPath (Join-Path $data "auto.cnf")) -or
    -not (Test-Path -LiteralPath (Join-Path $data "eduai"))) {
    throw "The expected initialized EduAI MySQL data directory was not found at $data"
}

function Test-MySqlPort {
    $socket = New-Object System.Net.Sockets.TcpClient
    try {
        $pending = $socket.BeginConnect("127.0.0.1", 3307, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(750)) { return $false }
        $socket.EndConnect($pending)
        return $socket.Connected
    } catch {
        return $false
    } finally {
        $socket.Dispose()
    }
}

# Match live MySQL processes by their actual command line, not just a PID or
# executable name. A PID can be reused by Windows after a server has exited.
$allMySqlProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'mysqld.exe'" -ErrorAction Stop)
$normalizedIni = $ini.Replace('/', '\')
$projectProcesses = @($allMySqlProcesses | Where-Object {
    $commandLine = ([string]$_.CommandLine).Replace('/', '\')
    $commandLine.IndexOf($normalizedIni, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
})

# If MySQL is listening, only shut it down when the listener is the process
# configured by this project's mysql_local.ini. Otherwise, leave other servers
# alone and abort before deleting any files.
$portInUse = Test-MySqlPort
if ($portInUse) {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 3307 -ErrorAction SilentlyContinue)
    $listenerIds = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    $projectIds = @($projectProcesses | Select-Object -ExpandProperty ProcessId)
    if ($listenerIds.Count -eq 0 -or @($listenerIds | Where-Object { $_ -notin $projectIds }).Count -gt 0) {
        throw "Port 3307 is active but its listener could not be verified as EduAI's MySQL process. No database files were deleted."
    }

    & $client "--defaults-file=$controlCnf" --connect-timeout=3 --execute="SHUTDOWN"
    if ($LASTEXITCODE -ne 0) { throw "Could not cleanly shut down the verified EduAI MySQL server. No database files were deleted." }
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline -and (Test-MySqlPort)) { Start-Sleep -Milliseconds 300 }
    if (Test-MySqlPort) { throw "EduAI MySQL did not stop cleanly. No database files were deleted." }
} else {
    # This handles the user's current case: the project server has a live PID
    # but its TCP listener is unavailable. Stop only a process whose command
    # line names this project's config; leave all other MySQL instances alone.
    foreach ($process in $projectProcesses) {
        $processPath = [string]$process.ExecutablePath
        if (-not $processPath -or [System.IO.Path]::GetFullPath($processPath) -ine [System.IO.Path]::GetFullPath($server)) {
            throw "A process uses this project's MySQL config but is not the configured MySQL 26.7 executable (PID $($process.ProcessId)). No database files were deleted."
        }
        Stop-Process -Id ([int]$process.ProcessId) -Force -ErrorAction Stop
        $deadline = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $deadline -and (Get-Process -Id ([int]$process.ProcessId) -ErrorAction SilentlyContinue)) {
            Start-Sleep -Milliseconds 250
        }
        if (Get-Process -Id ([int]$process.ProcessId) -ErrorAction SilentlyContinue) {
            throw "Could not stop verified EduAI MySQL process PID $($process.ProcessId). No database files were deleted."
        }
    }
}

if (Test-MySqlPort) { throw "Port 3307 is still active. No database files were deleted." }
$remainingProjectProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'mysqld.exe'" -ErrorAction Stop |
    Where-Object {
        $commandLine = ([string]$_.CommandLine).Replace('/', '\')
        $commandLine.IndexOf($normalizedIni, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
    })
if ($remainingProjectProcesses.Count -gt 0) {
    throw "EduAI MySQL is still running (PID $($remainingProjectProcesses[0].ProcessId)). No database files were deleted."
}

# Removing this directory recreates the MySQL system users and the eduai
# database from the project's private connection settings during installation.
Remove-Item -LiteralPath $data -Recurse -Force
Write-Output "Removed EduAI's dedicated MySQL data directory. Reinitializing the database and connection on MySQL 26.7..."
& (Join-Path $root "install_mysql.ps1")

Push-Location $root
try {
    & $python -c "from database import ensure_schema; ensure_schema(); print('EduAI SQL schema created.')"
    if ($LASTEXITCODE -ne 0) { throw "Creating the EduAI tables failed with exit code $LASTEXITCODE." }

    @'
from database import connect

expected = {
    "users", "eduai_catalog", "eduai_documents", "eduai_chat_messages",
    "eduai_practice_sessions", "eduai_admin_events",
}
connection = connect()
try:
    cursor = connection.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()[0]
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='eduai' AND table_type='BASE TABLE'"
    )
    tables = {row[0] for row in cursor.fetchall()}
    if not version.startswith("26.7"):
        raise RuntimeError(f"Expected MySQL 26.7; connected to {version}")
    if tables != expected:
        raise RuntimeError(f"Unexpected EduAI schema. Found: {sorted(tables)}")
    print(f"Verified app connection to MySQL {version}.")
    print("Verified EduAI tables:", ", ".join(sorted(tables)))
finally:
    connection.close()
'@ | & $python -
    if ($LASTEXITCODE -ne 0) { throw "The new application database connection did not pass verification." }

    if ($CreateAdmin) {
        Write-Output "Create the new Admin account now. Password input is hidden."
        & $python $adminScript
        if ($LASTEXITCODE -ne 0) { throw "Admin account setup failed with exit code $LASTEXITCODE." }
    }
} finally {
    Pop-Location
}

if ($CreateAdmin) {
    Write-Output "EduAI MySQL 26.7, connection, schema, and Admin account setup completed."
} else {
    Write-Output "EduAI MySQL 26.7, connection, and empty schema are ready. Run with -CreateAdmin to add the initial Admin account."
}
