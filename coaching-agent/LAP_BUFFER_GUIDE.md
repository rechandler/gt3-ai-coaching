# Lap Buffer System Guide

## Overview

The Lap Buffer System provides comprehensive lap and sector telemetry buffering for accurate "best lap," "rolling stint," and "compare to pro" functionality. This system segments telemetry into laps and sectors, stores and persists good reference laps, and provides real-time comparison data.

## Key Features

### 1. Real-Time Lap/Sector Buffering
- **Automatic lap completion detection** from telemetry data
- **Sector time calculation** with configurable sector boundaries
- **Telemetry point buffering** for detailed analysis
- **Real-time event generation** for lap and sector completions

### 2. Reference Lap Management
- **Personal best tracking** with automatic updates
- **Session best tracking** for current session performance
- **Sector best tracking** for individual sector improvements
- **Multiple reference types**: personal_best, session_best, optimal, consistency, race_pace

### 3. Persistence System
- **Per car/track reference storage** in JSON files
- **Automatic loading** of previous reference laps
- **Cross-session persistence** of personal bests
- **Metadata storage** for reference lap context

### 4. Rolling Stint Analysis
- **Performance trend analysis** over recent laps
- **Consistency scoring** for lap time variation
- **Improvement rate calculation** for coaching feedback
- **Race pace analysis** for endurance scenarios

## Architecture

### Core Components

1. **LapBufferManager** - Main buffering and tracking system
2. **ReferenceLapHelper** - Reference lap management and updates
3. **LapData** - Complete lap telemetry data structure
4. **SectorData** - Sector-specific telemetry and timing data
5. **ReferenceLap** - Reference lap for comparison

### Data Flow

```
Telemetry Input → LapBufferManager → Event Detection → Reference Updates → Persistence
     ↓              ↓                    ↓                ↓              ↓
Sector Buffers → Lap Completion → Reference Helper → File Storage → Cross-Session Loading
```

## Usage Examples

### Basic Integration

```python
from lap_buffer_manager import LapBufferManager
from reference_lap_helper import create_reference_lap_helper

# Initialize components
lap_buffer_manager = LapBufferManager()
reference_helper = create_reference_lap_helper(lap_buffer_manager)

# Set up track information
lap_buffer_manager.update_track_info(
    track_name="Spa-Francorchamps",
    car_name="BMW M4 GT3",
    sector_boundaries=[0.0, 0.33, 0.66, 1.0]  # 3 sectors
)

# Process telemetry
telemetry = {
    'lap': 1,
    'lapDistPct': 0.25,
    'speed': 150,
    'throttle': 85,
    'brake': 0,
    'steering': 0.1,
    'track_name': 'Spa-Francorchamps',
    'car_name': 'BMW M4 GT3'
}

# Buffer telemetry and check for events
lap_event = lap_buffer_manager.buffer_telemetry(telemetry)

if lap_event:
    if lap_event['type'] == 'lap_completed':
        lap_data = lap_event['lap_data']
        updates = reference_helper.check_and_update_reference_laps(lap_data)
        print(f"Lap completed: {lap_data.lap_time:.3f}s")
        
    elif lap_event['type'] == 'sector_completed':
        sector_data = lap_event['sector_data']
        print(f"Sector {sector_data.sector_number + 1}: {sector_data.sector_time:.3f}s")
```

### Reference Lap Management

```python
# Check for new personal bests
def on_reference_update(update_type: str, lap_data: LapData):
    if update_type == 'personal_best':
        print(f"🏆 NEW PERSONAL BEST: {lap_data.lap_time:.3f}s")
    elif update_type == 'sector_bests':
        print("📊 New sector bests achieved!")

# Register callback
reference_helper.register_reference_update_callback(on_reference_update)

# Get reference comparison
comparison = reference_helper.get_reference_comparison_summary('personal_best')
if comparison:
    delta = comparison['delta_to_reference']
    print(f"Delta to PB: {delta:.3f}s")
```

### Rolling Stint Analysis

```python
# Get rolling stint analysis
stint_analysis = reference_helper.get_rolling_stint_analysis()

if stint_analysis:
    print(f"Total laps: {stint_analysis['total_laps']}")
    print(f"Average lap time: {stint_analysis['avg_lap_time']:.3f}s")
    print(f"Consistency score: {stint_analysis['consistency_score']:.2f}")
    print(f"Trend: {stint_analysis['trend']}")
```

### Session Summary

```python
# Get comprehensive session summary
session_summary = reference_helper.get_session_summary()

print(f"Session best: {session_summary['session_best_lap']:.3f}s")
print(f"Personal best: {session_summary['personal_best_lap']:.3f}s")
print(f"Best sector times: {session_summary['best_sector_times']}")
print(f"Available references: {session_summary['reference_laps']['available_references']}")
```

## Integration with Coaching Agent

### Hybrid Coach Integration

The lap buffer system is integrated into the `HybridCoachingAgent`:

```python
# In HybridCoachingAgent.__init__()
self.lap_buffer_manager = LapBufferManager()

# In process_telemetry()
lap_event = self.lap_buffer_manager.buffer_telemetry(telemetry_data)
if lap_event:
    await self.handle_lap_event(lap_event, telemetry_data)
```

### Event Handling

```python
async def handle_lap_event(self, lap_event: Dict[str, Any], telemetry_data: Dict[str, Any]):
    event_type = lap_event.get('type')
    
    if event_type == 'lap_completed':
        lap_data = lap_event.get('lap_data')
        is_personal_best = lap_event.get('is_personal_best', False)
        
        # Create coaching message
        message_content = f"🏁 Lap {lap_data.lap_number} completed: {lap_data.lap_time:.3f}s"
        if is_personal_best:
            message_content += " 🏆 NEW PERSONAL BEST!"
        
        # Queue message
        await self.message_queue.add_message(coaching_message)
```

## Configuration

### Sector Boundaries

Configure sector boundaries based on track characteristics:

```python
# Standard 3-sector split
sector_boundaries = [0.0, 0.33, 0.66, 1.0]

# Custom 4-sector split for complex tracks
sector_boundaries = [0.0, 0.25, 0.50, 0.75, 1.0]

# Track-specific boundaries
track_sectors = {
    "Spa-Francorchamps": [0.0, 0.33, 0.66, 1.0],
    "Monza": [0.0, 0.25, 0.50, 0.75, 1.0],
    "Nürburgring Grand Prix": [0.0, 0.20, 0.40, 0.60, 0.80, 1.0]
}
```

### Reference Types

The system supports multiple reference types:

- **personal_best** - Fastest lap time achieved
- **session_best** - Best lap in current session
- **optimal** - Lap within 0.5% of personal best
- **consistency** - Lap showing good consistency
- **race_pace** - Lap suitable for race conditions

## Data Persistence

### File Structure

Reference laps are stored in JSON files:

```
lap_data/
├── Spa-Francorchamps_BMW M4 GT3_references.json
├── Monza_Ferrari 488 GT3_references.json
└── Nürburgring Grand Prix_Porsche 911 GT3 R_references.json
```

### File Format

```json
{
  "personal_best": {
    "lap_data": {
      "lap_number": 5,
      "lap_time": 89.234,
      "sector_times": [29.123, 30.456, 29.655],
      "track_name": "Spa-Francorchamps",
      "car_name": "BMW M4 GT3",
      "timestamp": 1640995200.0,
      "is_valid": true,
      "metadata": {
        "sector_boundaries": [0.0, 0.33, 0.66, 1.0],
        "telemetry_count": 1500
      }
    },
    "created_at": 1640995200.0,
    "metadata": {
      "track_name": "Spa-Francorchamps",
      "car_name": "BMW M4 GT3"
    }
  }
}
```

## Performance Considerations

### Memory Usage

- **Telemetry buffering**: ~500-1000 points per lap
- **Reference storage**: Minimal memory footprint
- **Session data**: Grows with session length

### Processing Overhead

- **Real-time buffering**: <1ms per telemetry point
- **Lap completion**: ~5ms processing time
- **Reference updates**: ~10ms for full analysis

### Storage Requirements

- **Per lap**: ~50KB telemetry data
- **Reference files**: ~10KB per track/car combination
- **Session data**: ~1MB per hour of driving

## Testing

### Run Comprehensive Tests

```bash
cd coaching-agent
python test_lap_buffer_system.py
```

### Test Components

1. **Basic lap buffering** - Real-time telemetry processing
2. **Reference persistence** - Cross-session data storage
3. **Sector analysis** - Detailed sector-by-sector tracking

## Troubleshooting

### Common Issues

1. **No lap events detected**
   - Check telemetry field names (`lap`, `lapDistPct`)
   - Verify sector boundaries configuration
   - Ensure track/car info is set

2. **Reference laps not loading**
   - Check file permissions in `lap_data/` directory
   - Verify JSON file format
   - Ensure track/car names match exactly

3. **Sector times inaccurate**
   - Verify sector boundaries configuration
   - Check telemetry frequency (should be 60Hz+)
   - Ensure lap distance percentage is accurate

### Debug Logging

Enable debug logging for detailed analysis:

```python
import logging
logging.getLogger('lap_buffer_manager').setLevel(logging.DEBUG)
```

## Advanced Features

### Custom Reference Types

Create custom reference types for specific use cases:

```python
def create_custom_reference(lap_data: LapData, reference_type: str):
    # Custom logic for reference qualification
    if custom_qualification_logic(lap_data):
        lap_buffer_manager.save_reference_lap(lap_data, reference_type)
```

### Sector-Specific Analysis

Analyze performance in specific sectors:

```python
def analyze_sector_performance(sector_number: int):
    sector_data = lap_buffer_manager.get_sector_data(sector_number)
    if sector_data:
        print(f"Sector {sector_number} analysis:")
        print(f"  Best time: {sector_data.best_time:.3f}s")
        print(f"  Average time: {sector_data.avg_time:.3f}s")
        print(f"  Consistency: {sector_data.consistency:.2f}")
```

### Real-Time Coaching Integration

Integrate with coaching system for real-time feedback:

```python
def on_sector_completed(sector_data: SectorData):
    if sector_data.sector_time < sector_data.best_time:
        coaching_message = f"📊 Great sector {sector_data.sector_number + 1}! "
        coaching_message += f"New best: {sector_data.sector_time:.3f}s"
        # Send to coaching system
```

## Conclusion

The Lap Buffer System provides a robust foundation for accurate lap timing, sector analysis, and reference lap management. By properly integrating this system, you can achieve:

- **Accurate "best lap" tracking** with automatic updates
- **Detailed "rolling stint" analysis** for race pace coaching
- **Comprehensive "compare to pro" functionality** with multiple reference types
- **Persistent reference data** across sessions and tracks
- **Real-time coaching feedback** based on lap and sector performance

This system enables sophisticated coaching features that help drivers improve their performance through detailed analysis and comparison with their best laps and professional reference data. 