@echo off
echo Starting GT3 AI Coaching System (New Modular Architecture)...
echo.

echo Starting Telemetry Service (Ports 9001, 9002)...
start "Telemetry Service" cmd /k "cd /d telemetry-server\services && python telemetry_service.py"

timeout /t 3 /nobreak > nul

echo Starting Coaching Data Service (Port 8082)...
start "Coaching Service" cmd /k "cd /d telemetry-server\services && python coaching_data_service.py"

echo.
echo Services starting with new architecture...
echo - Telemetry Service: ws://localhost:9001 (telemetry) + ws://localhost:9002 (session)
echo - Coaching Data Service: ws://localhost:8082 (UI + AI coaching)
echo.
echo Press any key to close this window...
pause > nul
