$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot "..\model\.venv\Scripts\python.exe"
$app = Join-Path $PSScriptRoot "app.py"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Model environment not found at $python. Run install_ai_requirements.ps1 after creating it."
}

$client = New-Object System.Net.Sockets.TcpClient
try {
    $pending = $client.BeginConnect("127.0.0.1", 3308, $null, $null)
    if (-not $pending.AsyncWaitHandle.WaitOne(500)) {
        throw "MySQL 26.7 is not accepting connections on 127.0.0.1:3308. Finish the MySQL Configurator setup and start its Windows service."
    }
    $client.EndConnect($pending)
} finally {
    $client.Dispose()
}

& $python -m streamlit run $app


