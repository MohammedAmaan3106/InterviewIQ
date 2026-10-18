@echo off
title InterviewIQ Server
echo ===========================================================
echo               Starting InterviewIQ Backend
echo ===========================================================

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Creating venv...
    python -m venv venv
    venv\Scripts\pip.exe install -r requirements.txt
)

echo [*] Checking local computer vision models...
venv\Scripts\python.exe backend\models\download_models.py

echo.
echo [✓] Starting InterviewIQ server at http://127.0.0.1:8000
echo [✓] Open your browser and navigate to: http://127.0.0.1:8000
echo [✓] Press CTRL+C to terminate the server.
echo.

venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
