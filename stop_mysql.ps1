$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$server = "C:\Program Files\MySQL\MySQL Server 26.7\bin\mysqld.exe"
$client = "C:\Program Files\MySQL\MySQL Server 26.7\bin\mysql.exe"
$control = Join-Path $root ".mysql-control.cnf"
if (-not (Test-Path -LiteralPath $control)) { throw "Private MySQL shutdown credentials are missing: $control" }
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
if (-not (Test-MySqlPort)) { Write-Output "EduAI MySQL is already stopped."; exit 0 }
$matchingProcess = Get-Process -Name mysqld -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $server } |
    Select-Object -First 1
if (-not $matchingProcess) { throw "Port 3307 accepts connections, but the MySQL 26.7 process could not be verified. No shutdown command was sent." }
& $client "--defaults-file=$control" --execute="SHUTDOWN"
if ($LASTEXITCODE -ne 0) { throw "MySQL shutdown command failed with exit code $LASTEXITCODE." }
$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    if (-not (Test-MySqlPort)) { Write-Output "EduAI MySQL stopped cleanly."; exit 0 }
}
throw "MySQL accepted SHUTDOWN but the listener remains active."
