# Unicode Encoding Fix for GT3 AI Coaching

## Problem

The GT3 AI Coaching application was experiencing `UnicodeEncodeError: 'charmap' codec can't encode characters` errors on Windows due to Unicode characters (degree symbols °) in temperature messages.

## Root Cause

- Windows uses the legacy 'charmap' codec by default
- The AI coach was using degree symbols (°) in temperature messages like "tire overheating (200°F)"
- Python's default encoding couldn't handle these Unicode characters

## Solution Applied

### 1. **Fixed Unicode Characters**

- Replaced all degree symbols (°) with plain "F" in temperature messages
- Updated messages from `200°F` to `200F` for Windows compatibility

### 2. **Added UTF-8 Encoding Support**

- Added encoding headers to Python files: `# -*- coding: utf-8 -*-`
- Configured stdout/stderr to use UTF-8 encoding on Windows
- Set `PYTHONIOENCODING=utf-8` environment variable

### 3. **Updated Log File Encoding**

- Added `encoding='utf-8'` to RotatingFileHandler
- Ensures log files can handle Unicode characters properly

### 4. **Created Startup Scripts**

- `start_server.py` - Python startup script with encoding fixes
- `start-server.bat` - Windows batch file with proper environment variables

## Files Modified

### Python Server Files:

- `telemetry-server.py` - Added UTF-8 encoding configuration
- `ai_coach.py` - Replaced degree symbols, added encoding support
- `start_server.py` - New startup script with Unicode handling
- `start-server.bat` - Windows batch file for easy startup

### Build Configuration:

- `.github/workflows/build.yml` - Added UTF-8 environment variables
- Updated Python setup in CI/CD pipeline

## How to Use

### Option 1: Use the Batch File (Recommended for Windows)

```cmd
start-server.bat
```

### Option 2: Manual Python Startup

```powershell
cd python-server
$env:PYTHONIOENCODING="utf-8"
python start_server.py
```

### Option 3: Direct Server Start

```powershell
cd python-server
$env:PYTHONIOENCODING="utf-8"
python telemetry-server.py
```

## Verification

The following temperature messages now work without Unicode errors:

- ✅ "LF tire overheating (200F) - ease off the pace"
- ✅ "RF brake getting hot (180F) - ease brake pressure"
- ✅ "RR tire cold (150F) - push harder to warm up"

## Environment Variables Set

- `PYTHONIOENCODING=utf-8` - Forces UTF-8 encoding for I/O
- `PYTHONUTF8=1` - Enables UTF-8 mode (Python 3.7+)

This fix ensures the GT3 AI Coaching server runs smoothly on Windows without Unicode encoding errors while maintaining all coaching functionality.
