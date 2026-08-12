# Set local directory paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($scriptDir)) { $scriptDir = Get-Location }
$modelsDir = Join-Path $scriptDir "ollama_bin\models"
$homeDir = Join-Path $scriptDir "ollama_bin\data"

# Create directories if they don't exist
New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null
New-Item -ItemType Directory -Force -Path $homeDir | Out-Null

# Set environment variables for the current process session
$env:OLLAMA_MODELS = $modelsDir
$env:OLLAMA_HOME = $homeDir

Write-Host "Starting Ollama server locally..."
Write-Host "Models path: $modelsDir"
Write-Host "Home path: $homeDir"

# Run ollama serve
& (Join-Path $scriptDir "ollama_bin\ollama.exe") serve
