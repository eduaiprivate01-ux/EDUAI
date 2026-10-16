$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot "..\model\.venv\Scripts\python.exe"
$page = Join-Path $PSScriptRoot "tutor_accuracy_check.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "EduAI's Python environment is missing at $python. Run .\install_ai_requirements.ps1 first."
}
if (-not (Test-Path -LiteralPath $page)) {
    throw "The standalone accuracy-check page was not found at $page."
}

Set-Location -LiteralPath $PSScriptRoot
& $python -m streamlit run $page --server.address 127.0.0.1 --server.port 8502 --server.headless false --browser.gatherUsageStats false
if ($LASTEXITCODE -ne 0) {
    throw "The accuracy-check page stopped with exit code $LASTEXITCODE. Review the messages above."
}
