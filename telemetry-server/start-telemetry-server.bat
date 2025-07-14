@echo off
echo GT3 AI Coaching - Starting Telemetry Server Services
echo ================================================

cd /d "%~dp0services"

echo.
echo Starting modular telemetry services...
echo Architecture: iRacing SDK → Telemetry Service → Coaching Data Service → React UI
echo.
echo Services will start on:
echo   📊 Telemetry Service:     ws://localhost:9001 (telemetry), ws://localhost:9002 (session)
echo   📈 Coaching Data Service: ws://localhost:8082 (UI interface)
echo.

python launcher.py

pause
