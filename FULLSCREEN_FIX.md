# Fullscreen Mode Fix for GT3 AI Coaching Overlay

## Problem

When using Alt+Enter in iRacing to enter fullscreen borderless mode, the overlay widgets were not visible or interactive.

## Solution Applied

The following changes have been made to ensure the overlay works properly in fullscreen mode:

### 1. Enhanced Electron Window Configuration

- Added `focusable: false` to prevent stealing focus from the game
- Added `visibleOnAllWorkspaces: true` for better cross-workspace visibility
- Added `fullscreenable: false` to prevent accidental fullscreen
- Implemented periodic check to ensure the window stays on top

### 2. Maximum Z-Index Values

- Set all overlay elements to use the maximum z-index value (2147483647)
- This ensures they appear above fullscreen applications

### 3. Improved CSS for Fullscreen Compatibility

- Made the root container use fixed positioning with maximum z-index
- Set `pointer-events: none` on the main container to allow game clicks to pass through
- Set `pointer-events: auto` on interactive widgets to ensure they remain clickable

### 4. Enhanced Window Management

- Added automatic re-application of `alwaysOnTop` every 5 seconds
- Improved window level to 'screen-saver' priority for better visibility
- Added Windows-specific handling for fullscreen applications

## How to Test

1. Start the GT3 AI Coaching overlay
2. Launch iRacing
3. Press Alt+Enter to enter fullscreen borderless mode
4. The widgets should remain visible and interactive

## Hotkeys

- **F10**: Toggle overlay visibility
- **F11**: Toggle click-through mode (allows clicks to pass through to the game)

## Troubleshooting

If widgets are still not visible in fullscreen:

1. Press F10 twice to hide and show the overlay
2. Check the system tray and use "Force Show" option
3. Restart the overlay application
4. Make sure iRacing is in borderless fullscreen mode (Alt+Enter), not exclusive fullscreen

## Additional Notes

- The overlay now uses minimal system resources while maintaining visibility
- Click-through mode (F11) is useful when you want to interact with the game without accidentally clicking widgets
- The periodic check ensures compatibility with various fullscreen implementations
