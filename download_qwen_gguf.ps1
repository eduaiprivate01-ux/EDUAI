$ErrorActionPreference = "Stop"

$modelDirectory = Join-Path $PSScriptRoot "models\Qwen2.5-7B-Instruct-GGUF"
$modelFile = Join-Path $modelDirectory "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
$modelUrl = "https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
$expectedBytes = 4683074240

New-Item -ItemType Directory -Force -Path $modelDirectory | Out-Null
if ((Test-Path -LiteralPath $modelFile) -and (Get-Item -LiteralPath $modelFile).Length -eq $expectedBytes) {
    Write-Host "Qwen2.5-7B-Instruct Q4_K_M is already downloaded at $modelFile"
    exit 0
}

# --continue-at - resumes the large model download if power or network stops it.
& curl.exe --fail --location --retry 8 --retry-all-errors --continue-at - --progress-bar --output $modelFile $modelUrl
if ($LASTEXITCODE -ne 0) {
    throw "Qwen GGUF download stopped with exit code $LASTEXITCODE. Run this script again to resume it."
}

Write-Host "Qwen2.5-7B-Instruct Q4_K_M saved to $modelFile"
