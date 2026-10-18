# InterviewIQ - Windows 11 PowerShell Launch Script
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "               Starting InterviewIQ Backend                " -ForegroundColor White
Write-Host "===========================================================" -ForegroundColor Cyan

# Set location to the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Check for virtual environment
$pythonPath = Join-Path $scriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    Write-Host "[!] Virtual environment not found. Creating venv..." -ForegroundColor Yellow
    python -m venv venv
    & (Join-Path $scriptDir "venv\Scripts\pip.exe") install -r requirements.txt
}

# Verify local models exist, download if missing
$modelsDownloader = Join-Path $scriptDir "backend\models\download_models.py"
& $pythonPath $modelsDownloader

# Start FastAPI Uvicorn Server
Write-Host ""
Write-Host "[✓] Starting InterviewIQ server at http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "[✓] Open your browser and navigate to: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "[✓] Press CTRL+C in this terminal to stop the application." -ForegroundColor Yellow
Write-Host ""

& $pythonPath -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
