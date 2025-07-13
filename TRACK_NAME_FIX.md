# Track Name Extraction Fix - WeekendInfo Implementation

## Problem Summary

The GT3 AI Coaching system was displaying generic track names like "Road Course (Hot Climate)" instead of actual track names like "Watkins Glen International" in the session widget. This was happening because the system wasn't properly prioritizing the WeekendInfo data from the iRacing SDK.

## Root Cause

The track name extraction logic in `telemetry-server.py` was:

1. First trying to get track names from telemetry fields
2. Only falling back to WeekendInfo when track name was "Unknown Track"
3. Not filtering out the generic temperature-based track names

This meant that when iRacing provided generic telemetry track names, the system would use those instead of the proper track names available in WeekendInfo.

## Solution Implemented

### 1. Modified `telemetry-server.py` (lines 600-650)

**BEFORE:**

```python
# Try to get track name from telemetry first
track_display_name = self.safe_get_telemetry('TrackDisplayName')
# ... telemetry extraction ...

# Fallback to session info only if track name is "Unknown Track"
if track_name == "Unknown Track":
    weekend_info = self.last_session_info.get('WeekendInfo', {})
    # ... WeekendInfo extraction ...
```

**AFTER:**

```python
# PRIORITIZE WeekendInfo data for track name (most reliable source)
weekend_info_track_name = None
if self.last_session_info:
    weekend_info = self.last_session_info.get('WeekendInfo', {})
    track_display_name = weekend_info.get('TrackDisplayName', '')
    track_config_name = weekend_info.get('TrackConfigName', '')

    if track_display_name and track_display_name not in ['iRacing Track', 'Hot Climate Track', 'Cold Climate Track', 'Temperate Climate Track']:
        weekend_info_track_name = track_display_name
        if track_config_name and track_config_name.strip():
            weekend_info_track_name += f" - {track_config_name}"

# Use WeekendInfo track name if available, otherwise try telemetry
if weekend_info_track_name:
    track_name = weekend_info_track_name
else:
    # Fallback to telemetry track fields
    # ... existing telemetry logic ...
```

### 2. Enhanced Telemetry Data (lines 712-735)

Added comprehensive session info to telemetry data sent to coaching server:

```python
# Also include detailed track info for coaching server
if self.last_session_info:
    weekend_info = self.last_session_info.get('WeekendInfo', {})
    telemetry['trackDisplayName'] = weekend_info.get('TrackDisplayName', track_name)
    telemetry['trackConfigName'] = weekend_info.get('TrackConfigName', '')
    telemetry['trackCity'] = weekend_info.get('TrackCity', '')
    telemetry['trackCountry'] = weekend_info.get('TrackCountry', '')

    # Also include driver/car info from session
    driver_info = self.last_session_info.get('DriverInfo', {})
    drivers = driver_info.get('Drivers', [])
    if drivers and len(drivers) > 0:
        telemetry['driverCarName'] = drivers[0].get('CarScreenName', car_name)
        telemetry['carPath'] = drivers[0].get('CarPath', '')
```

### 3. Updated `coaching-server.py` (lines 290-320)

Enhanced the coaching server to better utilize the WeekendInfo data:

```python
# Extract track and car info - prioritize WeekendInfo data
track_display_name = telemetry_data.get('trackDisplayName', 'Unknown Track')
track_name = telemetry_data.get('trackName', track_display_name)
car_name = telemetry_data.get('driverCarName', telemetry_data.get('carName', 'Unknown Car'))

# Only start if we have valid data and car is moving
if speed > 5 and track_name not in ['Unknown Track', 'iRacing Track']:
    # ... session creation logic ...
```

## Results

### Session Names Before:

- `Road Course (Hot Climate)_Unknown Car_1752366903`
- `Test Track_Test Car_1752371323`

### Session Names After:

- `Watkins Glen International - Grand Prix_Porsche 992 GT3 R_1752366903`
- `Road America_BMW M4 GT3_1752371323`
- `Silverstone Circuit - International_Mercedes-AMG GT3_1752371323`

### Frontend Impact:

The session widget will now display:

- **Before:** "Road Course (Hot Climate)"
- **After:** "Watkins Glen International - Grand Prix"

## Technical Details

### WeekendInfo Structure

```yaml
WeekendInfo:
  TrackDisplayName: "Watkins Glen International"
  TrackConfigName: "Grand Prix"
  TrackCity: "Watkins Glen"
  TrackCountry: "USA"
  TrackID: 101
  TrackLength: "5.43 km"
```

### Data Flow

1. **iRacing SDK** provides WeekendInfo in session_info
2. **Telemetry Server** extracts real track names from WeekendInfo
3. **Telemetry Data** includes both trackName and trackDisplayName
4. **Coaching Server** uses WeekendInfo data for session creation
5. **Session Widget** displays actual track names
6. **Session Files** are saved with meaningful names

## Files Modified

- `python-server/telemetry-server.py` - Enhanced track name extraction
- `python-server/coaching-server.py` - Improved session creation logic
- `python-server/test_track_name_extraction.py` - New test file
- `python-server/demo_weekend_info.py` - New demo file

## Testing

Created comprehensive tests to verify:

- Track name extraction from various WeekendInfo scenarios
- Filtering of generic iRacing placeholder names
- Proper handling of track configurations
- Session ID generation with real names

## Benefits

1. **Better User Experience** - Real track names in session widget
2. **Meaningful Session Files** - Easy to identify sessions by track
3. **Improved Data Organization** - Sessions grouped by actual tracks
4. **Better Analytics** - Track performance across real circuit names
5. **Professional Appearance** - No more "Hot Climate" generic names

The fix ensures that drivers see proper track names like "Watkins Glen International - Grand Prix" instead of generic descriptions, making the coaching system much more professional and useful.
