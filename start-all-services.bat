@echo off
REM GT3 AI Coaching System - Unified Service Launcher
REM ================================================

REM Start Telemetry Service (Ports 9001, 9002)
echo Starting Telemetry Service (Ports 9001, 9002)...
start "Telemetry Service" cmd /k "cd /d telemetry-server\services && python telemetry_service.py"

REM Wait a moment to stagger service startup
timeout /t 3 /nobreak > nul

REM Start Coaching Agent (no direct port, but may be configured in coaching-agent/main.py)
echo Starting Coaching Agent...
start "Coaching Agent" cmd /k "cd /d coaching-agent && python main.py"

echo.
echo Services started:
echo - Telemetry Service: ws://localhost:9001 (telemetry), ws://localhost:9002 (session)
echo - Coaching Agent:    (see coaching-agent/main.py for API/config)
echo.
echo All services are running in separate windows.
pause > nul 