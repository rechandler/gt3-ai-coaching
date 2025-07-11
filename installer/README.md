# GT3 AI Coaching Installer

This directory contains the Windows installer configuration for GT3 AI Coaching.

## Prerequisites

1. **NSIS (Nullsoft Scriptable Install System)**

   - Download from: https://nsis.sourceforge.io/
   - Install and add to your PATH environment variable

2. **Built Application**
   - Run `npm run build` in the root directory first
   - This creates the `build` folder with the compiled Electron app

## Building the Installer

### Quick Build

```bash
cd installer
build-installer.bat
```

### Manual Build

```bash
makensis gt3-ai-coaching-installer.nsi
```

## Installer Features

✅ **Professional Windows Installer**

- Modern UI with custom branding
- Component selection (main app, shortcuts)
- Proper registry entries for Add/Remove Programs
- Automatic uninstaller creation
- Admin rights handling

✅ **Installation Options**

- Main application (required)
- Desktop shortcut (optional)
- Start Menu shortcuts (optional)

✅ **Smart Upgrade Handling**

- Detects previous installations
- Automatic uninstall of old versions
- Preserves user settings

## Customization

### Assets Directory

Create an `assets` folder with custom graphics:

- `icon.ico` - 48x48 application icon
- `header.bmp` - 150x57 installer header image
- `wizard.bmp` - 164x314 welcome page image

### Configuration

Edit `gt3-ai-coaching-installer.nsi` to customize:

- App version and metadata
- Installation options
- Registry settings
- File associations

## Output

The installer will be created as:

```
GT3-AI-Coaching-Setup-v1.0.0.exe
```

## Distribution

The generated `.exe` file is a complete standalone installer that includes:

- The Electron application
- Python telemetry server
- All dependencies
- Uninstaller

Users can simply run the `.exe` file to install GT3 AI Coaching on their Windows system.

## Testing

Before distribution, test the installer:

1. Run the installer as administrator
2. Test all installation options
3. Verify the application launches correctly
4. Test the uninstaller
5. Check Add/Remove Programs entry

## File Structure

```
installer/
├── gt3-ai-coaching-installer.nsi  # Main NSIS script
├── build-installer.bat            # Build script
├── license.txt                    # Software license
├── assets/                        # Custom graphics (optional)
│   ├── icon.ico
│   ├── header.bmp
│   └── wizard.bmp
└── README.md                      # This file
```
