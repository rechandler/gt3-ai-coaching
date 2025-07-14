@echo off
echo Starting GT3 Coaching Agent...

REM Change to the coaching-agent directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create default config if it doesn't exist
if not exist "coaching_config.json" (
    echo Creating default configuration...
    python config.py
)

REM Start the coaching agent
echo Starting coaching agent...
python main.py %*

pause
