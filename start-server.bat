@echo off
REM GT3 AI Coaching Server Startup Script (New Modular Architecture)
REM Fixes Unicode encoding issues on Windows

echo Starting GT3 AI Coaching Services...

REM Set environment variables for UTF-8 encoding
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM Change to telemetry-server directory
cd /d "%~dp0telemetry-server\services"

REM Start the coaching data service with proper encoding
echo Starting Coaching Data Service...
python coaching_data_service.py

pause
