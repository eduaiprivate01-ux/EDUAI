$ErrorActionPreference = "Stop"

# EduAI shares the already-created local model environment next to this folder.
$python = Join-Path $PSScriptRoot "..\model\.venv\Scripts\python.exe"
$requirements = Join-Path $PSScriptRoot "requirements.txt"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Model environment not found at $python. Create the model .venv first."
}

# The extra index provides the prebuilt CPU wheel for llama-cpp-python on Windows.
& $python -m pip install --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/cpu" -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw "Python dependency installation failed with exit code $LASTEXITCODE."
}

Write-Host "EduAI AI/RAG requirements are installed in the model virtual environment."
