$ErrorActionPreference = "Stop"

# Reuse the same local virtual environment as the rest of EduAI.
$python = Join-Path $PSScriptRoot "..\model\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Model environment not found at $python. Install project requirements first."
}

& $python (Join-Path $PSScriptRoot "download_reranker.py")
if ($LASTEXITCODE -ne 0) {
    throw "Reranker download failed with exit code $LASTEXITCODE. Rerun this script to resume."
}
