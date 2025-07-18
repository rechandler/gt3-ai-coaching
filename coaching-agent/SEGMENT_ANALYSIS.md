# Segment Analysis Feature

## Overview

The segment analysis feature provides track-specific coaching feedback by analyzing telemetry data in the context of track segments (corners, straights, chicanes). This enables more precise and actionable coaching advice.

## Architecture

### Components

1. **TrackMetadataManager** (`track_metadata_manager.py`)
   - Manages track segment definitions
   - Hybrid approach: Firebase caching + local fallback + LLM generation
   - Supports dynamic track loading

2. **SegmentAnalyzer** (`segment_analyzer.py`)
   - Buffers telemetry data by segment
   - Analyzes performance metrics per segment
   - Generates segment-specific feedback

3. **Integration** (`hybrid_coach.py`)
   - Integrates segment analysis into the coaching agent
   - Delivers feedback through the message queue

## Track Metadata

### Structure
```json
{
  "name": "Eau Rouge",
  "start_pct": 0.03,
  "end_pct": 0.08,
  "type": "corner",
  "description": "Famous uphill left-right complex"
}
```

### Segment Types
- `corner`: Turns and curves
- `straight`: High-speed sections
- `chicane`: Complex corner sequences

## Analysis Metrics

### Per Segment
- Entry/exit speed
- Average throttle/brake usage
- Maximum steering input
- Speed variance
- Throttle/brake consistency
- Segment time

### Feedback Categories
- **Corner-specific**: Throttle timing, steering input, speed carrying
- **Straight-specific**: Full throttle usage, speed optimization
- **Chicane-specific**: Smooth inputs, throttle application

## Usage

### Basic Usage
```python
from track_metadata_manager import TrackMetadataManager
from segment_analyzer import SegmentAnalyzer

# Initialize
track_manager = TrackMetadataManager()
segment_analyzer = SegmentAnalyzer(track_manager)

# Load track metadata
segments = await track_manager.get_track_metadata("Spa-Francorchamps")
segment_analyzer.update_track("Spa-Francorchamps", segments)

# Process telemetry
segment_analyzer.buffer_telemetry(telemetry_data)
```

### Integration with Coaching Agent
The segment analysis is automatically integrated into the `HybridCoachingAgent`:

1. **Track Detection**: Automatically detects track changes
2. **Metadata Loading**: Loads track segments from Firebase/local cache
3. **Telemetry Buffering**: Buffers data by segment during driving
4. **Lap Analysis**: Analyzes completed laps and generates feedback
5. **Feedback Delivery**: Sends coaching messages through the message queue

## Configuration

### Firebase Setup (Optional)
```python
# Initialize with Firebase
track_manager = TrackMetadataManager("path/to/firebase-config.json")
```

### Local-Only Mode
```python
# Use local cache only
track_manager = TrackMetadataManager()
```

## Testing

Run the test script to see segment analysis in action:
```bash
python test_segment_analysis.py
```

## Available Tracks

Currently supported tracks:
- Spa-Francorchamps
- Nürburgring Grand Prix
- Monza

## LLM Integration

The system now supports LLM-powered track metadata generation:

### Setup
```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

### How It Works
1. **Firebase Check**: First tries to load from Firebase cache
2. **Local Fallback**: Falls back to local file cache
3. **LLM Generation**: Uses OpenAI API to generate metadata for new tracks
4. **Caching**: Generated metadata is cached locally and in Firebase

### Testing LLM Integration
```bash
# Test LLM generation
python test_llm_integration.py
```

### Example LLM-Generated Metadata
```json
[
  {
    "name": "Turn 1",
    "start_pct": 0.00,
    "end_pct": 0.05,
    "type": "corner",
    "description": "Tight right-hander after start/finish"
  },
  {
    "name": "Back Straight",
    "start_pct": 0.05,
    "end_pct": 0.15,
    "type": "straight",
    "description": "Long straight section"
  }
]
```

## Future Enhancements

1. **Advanced Metrics**: Tire wear, fuel consumption, weather effects
2. **Comparative Analysis**: Compare against reference laps
3. **Real-time Feedback**: Provide feedback during segments (not just after)
4. **Custom Segments**: Allow users to define custom track segments
5. **Multi-LLM Support**: Support for different LLM providers

## Performance Considerations

- **Memory Usage**: Segment buffers are cleared after lap analysis
- **Processing**: Analysis runs after lap completion to avoid real-time overhead
- **Feedback Rate**: Cooldown prevents feedback spam (5-second minimum)
- **Caching**: Firebase and local caching reduce metadata loading time 