# Fullscreen Mode, Delta Time & Widget Updates for GT3 AI Coaching Overlay

## Problems Addressed

1. **Fullscreen Mode**: When using Alt+Enter in iRacing to enter fullscreen borderless mode, the overlay widgets were not visible or interactive.
2. **Delta Time Not Working**: The delta time widget was showing "0.000" instead of actual delta time values.
3. **Removed Unavailable Data**: Tire temperature and brake temperature widgets removed as iRacing doesn't provide this data through their telemetry API.

## Solutions Applied

### 1. Fullscreen Mode Fix

#### Enhanced Electron Window Configuration

- Added `focusable: false` to prevent stealing focus from the game
- Added `visibleOnAllWorkspaces: true` for better cross-workspace visibility
- Added `fullscreenable: false` to prevent accidental fullscreen
- Implemented periodic check to ensure the window stays on top

#### Maximum Z-Index Values

- Set all overlay elements to use the maximum z-index value (2147483647)
- This ensures they appear above fullscreen applications

#### Improved CSS for Fullscreen Compatibility

- Made the root container use fixed positioning with maximum z-index
- Set `pointer-events: none` on the main container to allow game clicks to pass through
- Set `pointer-events: auto` on interactive widgets to ensure they remain clickable

#### Enhanced Window Management

- Added automatic re-application of `alwaysOnTop` every 5 seconds
- Improved window level to 'screen-saver' priority for better visibility
- Added Windows-specific handling for fullscreen applications

### 2. Delta Time Fix

#### Use iRacing's Built-in Delta Fields

- Now uses `LapDeltaToBestLap` (primary) for more accurate delta calculation
- Falls back to `LapDeltaToOptimalLap` if best lap delta not available
- Falls back to `LapDeltaToSessionBestLap` for session comparison
- Manual calculation as final fallback using current vs best lap time

#### Enhanced Debug Information

- Added console logging for delta data reception
- Widget shows delta type (best/optimal/session/manual) for debugging
- Shows "No delta data" message when no data is available

#### Improved Delta Display

- Better color coding: Green for negative (faster), Red for positive (slower)
- Shows delta type in the widget subtitle
- Handles edge cases when no best lap is set yet

### 3. Widget Cleanup

#### Removed Unavailable Widgets

- **Tire Temperature Widget**: Removed as iRacing doesn't provide tire temperature data through their telemetry API
- **Brake Temperature Widget**: Removed as iRacing doesn't provide brake temperature data through their telemetry API
- **Reorganized Layout**: Remaining widgets repositioned for better screen utilization

## How to Test

1. Start the GT3 AI Coaching overlay
2. Launch iRacing
3. Press Alt+Enter to enter fullscreen borderless mode
4. The widgets should remain visible and interactive

## Hotkeys

- **F10**: Toggle overlay visibility
- **F11**: Toggle click-through mode (allows clicks to pass through to the game)

## Troubleshooting

### Fullscreen Mode Issues

If widgets are still not visible in fullscreen:

1. Press F10 twice to hide and show the overlay
2. Check the system tray and use "Force Show" option
3. Restart the overlay application
4. Make sure iRacing is in borderless fullscreen mode (Alt+Enter), not exclusive fullscreen

### Delta Time Issues

If delta time shows "0.000" or "No delta data":

1. **Complete at least one lap** - Delta time requires a best lap to compare against
2. **Check console logs** - Open DevTools (F12) and look for "Delta data:" messages
3. **Verify iRacing connection** - Make sure the connection indicator shows "iRacing Connected"
4. **Test delta fields** - Run `python test_delta.py` in the python-server folder to verify iRacing is providing delta data
5. **Restart both applications** - Close GT3 AI Coaching and restart, then restart iRacing session

### Debug Steps for Delta Time

1. Open browser DevTools (F12) while overlay is running
2. Look for "Delta data:" console messages showing:
   - `deltaTime`: The actual delta value
   - `deltaType`: Which type of delta is being used (best/optimal/session/manual/none)
   - `onPitRoad`: Whether you're in the pits
3. If `deltaType` shows "none", you need to complete a lap to establish a baseline

## Additional Notes

### AI Coaching Widget Improvements

- **Multiple Messages**: Can display up to 3 coaching messages simultaneously
- **Minimum Display Time**: Messages stay visible for at least 5 seconds (4 seconds for secondary messages)
- **Duplicate Prevention**: Identical messages are filtered out to avoid spam
- **Priority System**: Higher priority messages are displayed prominently
- **Auto-Expiration**: Messages automatically disappear after their display time
- **Message Counter**: Shows number of active messages when multiple are present
- **Timestamp Display**: Shows how long each message has been displayed with expiration warning

### Fuel Widget Improvements

- **Accurate Lap Calculation**: Uses actual fuel consumption data from completed laps
- **Multiple Calculation Methods**: Falls back through 5 different calculation methods for accuracy
- **Real-Time Tracking**: Monitors fuel usage per lap and adapts to your driving style
- **Session Learning**: Calculates session average fuel consumption for better estimates
- **Debug Information**: Shows fuel per lap and calculation method used
- **Smart Filtering**: Ignores unrealistic fuel usage data (pit stops, anomalies)

### Performance Optimizations

- The overlay now uses minimal system resources while maintaining visibility
- Click-through mode (F11) is useful when you want to interact with the game without accidentally clicking widgets
- The periodic check ensures compatibility with various fullscreen implementations
- Message history is cleared every 5 minutes to prevent memory buildup
