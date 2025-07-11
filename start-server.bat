@echo off
REM GT3 AI Coaching Server Startup Script
REM Fixes Unicode encoding issues on Windows

echo Starting GT3 AI Coaching Server...

REM Set environment variables for UTF-8 encoding
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM Change to python-server directory
cd /d "%~dp0python-server"

REM Start the server with proper encoding
python start_server.py

pause
