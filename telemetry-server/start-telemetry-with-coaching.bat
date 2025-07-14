@echo off
echo Starting GT3 Telemetry Server with AI Coaching...

REM Change to the telemetry-server directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if coaching agent is available
if exist "..\coaching-agent\config.py" (
    echo Coaching agent found - installing coaching dependencies...
    pip install -r ..\coaching-agent\requirements.txt
) else (
    echo Warning: Coaching agent not found. Running telemetry server without AI coaching.
)

REM Set environment variables for coaching
set PYTHONPATH=%PYTHONPATH%;..\coaching-agent

REM Start the telemetry service launcher
echo Starting telemetry services...
python services\launcher.py

pause
