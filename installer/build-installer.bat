@echo off
echo Building GT3 AI Coaching Windows Installer...
echo.

REM Check if NSIS is installed
where makensis >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: NSIS not found in PATH!
    echo Please install NSIS from https://nsis.sourceforge.io/
    echo Make sure to add NSIS to your PATH environment variable.
    pause
    exit /b 1
)

REM Check if build directory exists
if not exist "..\build" (
    echo ERROR: Build directory not found!
    echo Please run 'npm run build' first to create the Electron build.
    pause
    exit /b 1
)

REM Create installer assets directory if it doesn't exist
if not exist "assets" mkdir assets

REM Check for required assets
set missing_assets=0

if not exist "assets\icon.ico" (
    echo WARNING: assets\icon.ico not found - using default
    copy /y "default-icon.ico" "assets\icon.ico" >nul 2>nul
)

if not exist "assets\header.bmp" (
    echo WARNING: assets\header.bmp not found - installer will use default
    set missing_assets=1
)

if not exist "assets\wizard.bmp" (
    echo WARNING: assets\wizard.bmp not found - installer will use default
    set missing_assets=1
)

if not exist "license.txt" (
    echo Creating default license file...
    echo MIT License > license.txt
    echo. >> license.txt
    echo Copyright (c) 2025 GT3 Racing Solutions >> license.txt
    echo. >> license.txt
    echo Permission is hereby granted, free of charge, to any person obtaining a copy >> license.txt
    echo of this software and associated documentation files (the "Software"), to deal >> license.txt
    echo in the Software without restriction, including without limitation the rights >> license.txt
    echo to use, copy, modify, merge, publish, distribute, sublicense, and/or sell >> license.txt
    echo copies of the Software, and to permit persons to whom the Software is >> license.txt
    echo furnished to do so, subject to the following conditions: >> license.txt
    echo. >> license.txt
    echo The above copyright notice and this permission notice shall be included in all >> license.txt
    echo copies or substantial portions of the Software. >> license.txt
    echo. >> license.txt
    echo THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR >> license.txt
    echo IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, >> license.txt
    echo FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE >> license.txt
    echo AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER >> license.txt
    echo LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, >> license.txt
    echo OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE >> license.txt
    echo SOFTWARE. >> license.txt
)

echo Building installer with NSIS...
makensis gt3-ai-coaching-installer.nsi

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ SUCCESS: Installer created successfully!
    echo 📦 File: GT3-AI-Coaching-Setup-v1.0.0.exe
    echo.
    if %missing_assets% equ 1 (
        echo 💡 TIP: Add custom graphics to the assets folder:
        echo    - assets\icon.ico (48x48 app icon)
        echo    - assets\header.bmp (150x57 header image)
        echo    - assets\wizard.bmp (164x314 welcome image)
        echo.
    )
    echo Ready for distribution! 🚀
) else (
    echo.
    echo ❌ ERROR: Failed to create installer
    echo Check the NSIS output above for details.
)

echo.
pause
