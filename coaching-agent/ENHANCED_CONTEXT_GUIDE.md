# Enhanced Context Guide for GT3 AI Coaching

## Overview

The Enhanced Context system implements structured JSON context with time-series data aggregation, providing comprehensive coaching intelligence with sliding window buffers and detailed event analysis.

## Key Features

### A. Data Aggregation
- **Sliding Window Buffers**: 10-30 second buffers with configurable duration
- **Time-Series Data**: Continuous telemetry capture at 60Hz
- **Event-Triggered Analysis**: Fetch data before/during/after events

### B. Structured JSON Context
- **Nested Information**: Hierarchical data organization
- **Time-Series Arrays**: Driver inputs, car state, tire data
- **Reference Comparisons**: Best lap, optimal values, deltas
- **Event History**: Pattern recognition and trend analysis

## Implementation

### Enhanced Context Builder

```python
from enhanced_context_builder import EnhancedContextBuilder

# Initialize with configuration
builder = EnhancedContextBuilder({
    'buffer_duration': 30.0,  # 30 seconds
    'sample_rate': 60         # 60Hz
})

# Add telemetry data
builder.add_telemetry(telemetry_data)

# Build structured context
context = builder.build_structured_context(
    event_type="understeer",
    severity="high",
    location={
        "track": "Spa",
        "turn": 5,
        "segment": "mid-corner"
    }
)
```

### Structured Context Format

```json
{
  "event": {
    "type": "understeer",
    "severity": "high",
    "location": {
      "track": "Spa",
      "turn": 5,
      "segment": "mid-corner"
    },
    "time": "14:30:25.123"
  },
  "driver_inputs": {
    "steering_angle": [-5, -6, -12, -14],
    "brake": [0.3, 0.4, 0.55, 0.3],
    "throttle": [0.1, 0.1, 0.15, 0.3],
    "gear": [3, 3, 2, 2]
  },
  "car_state": {
    "speed_kph": [98, 87, 80, 95],
    "rpm": [7100, 6900, 6700, 7200],
    "slip_angle": [-2, -6, -8, -7]
  },
  "tire_state": {
    "temps": [81, 80, 82, 85],
    "pressures": [24.5, 24.6, 24.7, 24.8]
  },
  "reference": {
    "best_apex_speed": 87,
    "driver_apex_speed": 80,
    "sector_delta_s": 0.18
  },
  "history": [
    {"lap": 5, "turn": 5, "event": "understeer", "severity": "medium"},
    {"lap": 6, "turn": 5, "event": "understeer", "severity": "high"}
  ],
  "session": {
    "type": "practice",
    "lap_number": 6,
    "fuel_remaining_l": 22
  }
}
```

## Data Dimensions

### 1. Event Information
```json
"event": {
  "type": "understeer|oversteer|offtrack|bad_exit|missed_apex",
  "severity": "low|medium|high",
  "location": {
    "track": "Track Name",
    "turn": "Turn Number/Name",
    "segment": "entry|mid-corner|exit|straight"
  },
  "time": "HH:MM:SS.mmm"
}
```

### 2. Driver Inputs (Time-Series)
```json
"driver_inputs": {
  "steering_angle": [-5, -6, -12, -14],  // Degrees
  "brake": [0.3, 0.4, 0.55, 0.3],        // 0-1 normalized
  "throttle": [0.1, 0.1, 0.15, 0.3],     // 0-1 normalized
  "gear": [3, 3, 2, 2]                    // Gear number
}
```

### 3. Car State (Time-Series)
```json
"car_state": {
  "speed_kph": [98, 87, 80, 95],         // Speed in km/h
  "rpm": [7100, 6900, 6700, 7200],       // Engine RPM
  "slip_angle": [-2, -6, -8, -7]         // Calculated slip angle
}
```

### 4. Tire State (Time-Series)
```json
"tire_state": {
  "temps": [81, 80, 82, 85],             // Tire temperatures
  "pressures": [24.5, 24.6, 24.7, 24.8]  // Tire pressures
}
```

### 5. Reference Data
```json
"reference": {
  "best_apex_speed": 87,                  // Optimal apex speed
  "driver_apex_speed": 80,                // Driver's apex speed
  "sector_delta_s": 0.18                  // Time delta to best
}
```

### 6. Event History
```json
"history": [
  {
    "lap": 5,
    "turn": 5,
    "event": "understeer",
    "severity": "medium"
  }
]
```

### 7. Session Information
```json
"session": {
  "type": "practice|qualify|race",
  "lap_number": 6,
  "fuel_remaining_l": 22
}
```

## Configuration Options

### Buffer Settings
```python
config = {
    'buffer_duration': 30.0,    # Buffer duration in seconds
    'sample_rate': 60,          # Sampling rate in Hz
    'event_window': 2.0         # Event analysis window
}
```

### Event Types
```python
EVENT_TYPES = {
    'understeer': 'Front tires losing grip',
    'oversteer': 'Rear tires losing grip',
    'offtrack': 'Car leaving track surface',
    'bad_exit': 'Poor corner exit speed',
    'missed_apex': 'Incorrect apex timing',
    'late_braking': 'Braking too late',
    'early_throttle': 'Throttle application too early'
}
```

### Severity Levels
```python
SEVERITY_LEVELS = {
    'low': 'Minor issue, minimal time loss',
    'medium': 'Moderate issue, noticeable time loss',
    'high': 'Major issue, significant time loss or safety concern'
}
```

## Integration with Coaching System

### 1. Telemetry Processing
```python
# Add telemetry to buffer
builder.add_telemetry(telemetry_data)

# Buffer automatically manages:
# - Time-series data storage
# - Sliding window updates
# - Data normalization
# - Unit conversions
```

### 2. Event Detection
```python
# When coaching insight is generated
context = builder.build_structured_context(
    event_type="understeer",
    severity="high",
    location={"track": "Spa", "turn": 5, "segment": "mid-corner"}
)
```

### 3. AI Prompting
```python
# Include structured context in AI prompts
prompt = f"""
Analyze this driving event with full context:

{json.dumps(context, indent=2)}

Provide specific coaching advice based on the time-series data and event history.
"""
```

## Advanced Features

### Time-Series Analysis
```python
# Analyze driver input patterns
steering_data = context['driver_inputs']['steering_angle']
brake_data = context['driver_inputs']['brake']
throttle_data = context['driver_inputs']['throttle']

# Calculate trends
steering_trend = analyze_trend(steering_data)
brake_trend = analyze_trend(brake_data)
throttle_trend = analyze_trend(throttle_data)
```

### Pattern Recognition
```python
# Identify recurring issues
history = context['history']
recurring_events = analyze_patterns(history)

# Example: Driver consistently understeering in Turn 5
if recurring_events.get('understeer', {}).get('turn_5', 0) > 3:
    coaching_focus = "Turn 5 entry technique"
```

### Reference Comparison
```python
# Compare to optimal performance
reference = context['reference']
current_speed = context['car_state']['speed_kph'][-1]
optimal_speed = reference['best_apex_speed']

speed_deficit = optimal_speed - current_speed
if speed_deficit > 5:
    coaching_focus = "Apex speed optimization"
```

## Testing

### Run Enhanced Context Tests
```bash
cd coaching-agent
python test_enhanced_context.py
```

### Test Categories
1. **Basic Functionality**: Structured context generation
2. **Time-Series Data**: Driver input progression
3. **Reference Data**: Performance comparisons
4. **Event History**: Pattern tracking
5. **Buffer Management**: Memory and performance

### Example Test Output
```
Testing Enhanced Context Builder...
Generated Structured Context:
{
  "event": {
    "type": "understeer",
    "severity": "high",
    "location": {"track": "Spa", "turn": 5, "segment": "mid-corner"},
    "time": "14:30:25.123"
  },
  "driver_inputs": {
    "steering_angle": [-5, -6, -12, -14],
    "brake": [0.3, 0.4, 0.55, 0.3],
    "throttle": [0.1, 0.1, 0.15, 0.3],
    "gear": [3, 3, 2, 2]
  },
  ...
}
```

## Performance Considerations

### Memory Management
- **Buffer Size**: Configurable based on memory constraints
- **Data Compression**: Efficient storage of time-series data
- **Garbage Collection**: Automatic cleanup of old data

### Processing Efficiency
- **Real-time Processing**: 60Hz telemetry handling
- **Event Detection**: Fast pattern matching
- **Context Building**: Optimized JSON generation

### API Integration
- **Structured Output**: Ready for AI/ML consumption
- **JSON Format**: Standard data interchange
- **Extensible**: Easy to add new data dimensions

## Best Practices

### 1. Event Classification
```python
# Use specific event types
event_type = classify_event(telemetry_data, analysis)

# Consider severity based on impact
severity = calculate_severity(time_loss, safety_risk)
```

### 2. Data Quality
```python
# Validate telemetry data
if not is_valid_telemetry(telemetry_data):
    logger.warning("Invalid telemetry data received")
    return

# Handle missing data gracefully
if not telemetry_data.get('speed'):
    telemetry_data['speed'] = estimate_speed(telemetry_data)
```

### 3. Performance Optimization
```python
# Configure buffer size based on requirements
if memory_constrained:
    buffer_duration = 10.0  # 10 seconds
else:
    buffer_duration = 30.0  # 30 seconds

# Monitor buffer statistics
stats = builder.get_buffer_stats()
logger.info(f"Buffer utilization: {stats['buffer_size']}/{stats['sample_rate']}")
```

### 4. Integration Patterns
```python
# Seamless integration with existing system
class EnhancedCoachingAgent:
    def __init__(self):
        self.context_builder = EnhancedContextBuilder()
        self.ai_coach = RemoteAICoach()
    
    async def process_telemetry(self, telemetry_data):
        # Add to buffer
        self.context_builder.add_telemetry(telemetry_data)
        
        # Detect events
        if self.detect_event(telemetry_data):
            context = self.context_builder.build_structured_context(
                event_type=self.get_event_type(),
                severity=self.get_event_severity(),
                location=self.get_event_location()
            )
            
            # Generate AI coaching
            coaching = await self.ai_coach.generate_coaching(context)
```

## Future Enhancements

### Planned Features
1. **Machine Learning Integration**
   - Train models on structured context data
   - Predictive event detection
   - Automated severity assessment

2. **Advanced Analytics**
   - Driver skill progression tracking
   - Setup optimization recommendations
   - Performance benchmarking

3. **Real-time Adaptation**
   - Dynamic coaching style adjustment
   - Session-based learning
   - Personalized coaching strategies

### API Extensions
```python
# Future API methods
builder.get_driver_profile()           # Driver skill assessment
builder.predict_next_issue()          # Predictive analysis
builder.optimize_setup()              # Setup recommendations
builder.get_improvement_plan()        # Personalized training plan
```

## Conclusion

The Enhanced Context system provides a comprehensive, structured approach to coaching data aggregation and analysis. By implementing time-series data capture, sliding window buffers, and structured JSON output, it enables:

- **Deeper AI Insights**: Rich, multi-dimensional context for AI analysis
- **Pattern Recognition**: Historical event tracking and trend analysis
- **Performance Comparison**: Reference data for optimal vs. actual performance
- **Personalized Coaching**: Session-specific and driver-specific insights

The system is designed to be:
- **Comprehensive**: Captures all relevant data dimensions
- **Efficient**: Optimized for real-time processing
- **Extensible**: Easy to add new data sources and analysis
- **Reliable**: Robust error handling and fallbacks

Start using enhanced context today to unlock the full potential of your GT3 AI coaching system! 