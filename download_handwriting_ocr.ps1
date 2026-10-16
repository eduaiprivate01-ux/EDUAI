$ErrorActionPreference = "Stop"

# Use the same Python environment as the LangChain, embedding, and Qwen pipeline.
$python = Join-Path $PSScriptRoot "..\model\.venv\Scripts\python.exe"
$downloader = Join-Path $PSScriptRoot "download_handwriting_ocr.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Model environment not found at $python. Create the model .venv and install requirements first."
}

& $python $downloader
if ($LASTEXITCODE -ne 0) {
    throw "Handwriting OCR model download failed with exit code $LASTEXITCODE. Rerun this script to resume."
}

Write-Host "Handwriting OCR model download is complete."
