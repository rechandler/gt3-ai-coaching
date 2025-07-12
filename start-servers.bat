@echo off
echo Starting GT3 AI Coaching System...
echo.

echo Starting Telemetry Server (Port 8081)...
start "Telemetry Server" cmd /k "cd /d python-server && python telemetry-server.py"

timeout /t 3 /nobreak > nul

echo Starting AI Coaching Server (Port 8082)...
start "Coaching Server" cmd /k "cd /d python-server && python coaching-server.py"

echo.
echo Both servers starting...
echo - Telemetry Server: ws://localhost:8081
echo - AI Coaching Server: ws://localhost:8082
echo.
echo Press any key to close this window...
pause > nul
