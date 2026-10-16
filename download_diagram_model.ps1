$ErrorActionPreference = "Stop"

# Ollama manages a local vision model; it is not a Python package and is not
# downloaded on every EduAI launch. Install Ollama once before running this file.
$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCommand) {
    throw "Ollama was not found. Install it once from https://ollama.com/download, reopen PowerShell, then rerun this script."
}

$versionOutput = & $ollamaCommand.Source --version
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the Ollama version. Update Ollama to version 0.7.0 or newer."
}
if ($versionOutput -match '(\d+\.\d+\.\d+)') {
    if ([version]$Matches[1] -lt [version]'0.7.0') {
        throw "Qwen2.5-VL requires Ollama 0.7.0 or newer. Installed version: $($Matches[1]). Update Ollama and rerun this script."
    }
}

$model = "qwen2.5vl:3b"
$dotenvPath = Join-Path $PSScriptRoot ".env"
if (Test-Path -LiteralPath $dotenvPath) {
    $modelSetting = Get-Content -LiteralPath $dotenvPath | Where-Object { $_ -match '^\s*EDUAI_VISION_MODEL\s*=' } | Select-Object -Last 1
    if ($modelSetting -match '^\s*EDUAI_VISION_MODEL\s*=\s*(.*?)\s*$') {
        $model = $Matches[1].Trim('"').Trim("'")
    }
}
if ($env:EDUAI_VISION_MODEL) { $model = $env:EDUAI_VISION_MODEL }
Write-Host "Downloading the local diagram-understanding model: $model"
Write-Host "The download is about 3.2 GB and is kept by Ollama for future runs."
& $ollamaCommand.Source pull $model
if ($LASTEXITCODE -ne 0) {
    throw "Ollama could not download $model. Check that Ollama is running and rerun this script."
}

Write-Host "Diagram vision model is ready. Keep Ollama running while using document extraction."
