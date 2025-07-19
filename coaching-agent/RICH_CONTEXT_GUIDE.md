# Rich Context Guide for GT3 AI Coaching

## Overview

The Rich Context system provides comprehensive, multi-dimensional data to your LLM/ML coaching prompts, enabling deeper insights and more personalized coaching advice. Instead of sending just "what just happened," you now send "why it happened," when/where it happened, and how it compares to targets or trends.

## Key Data Dimensions

### 1. Event Type
- **Purpose**: Identifies what happened (offtrack, oversteer, bad exit, etc.)
- **Example**: `'understeer'`, `'offtrack'`, `'late_braking'`
- **Usage**: Helps AI understand the specific driving issue

### 2. Car State
- **Purpose**: Current vehicle performance data
- **Data**: Speed, RPM, gear, throttle/brake/steering traces
- **Example**: 
  ```python
  {
    'speed': 95.0,
    'rpm': 5500,
    'gear': 3,
    'throttle_pct': 60.0,
    'brake_pct': 20.0,
    'steering_angle': 0.4
  }
  ```

### 3. Track State
- **Purpose**: Track and environmental information
- **Data**: Track name, segment, weather, lap position
- **Example**:
  ```python
  {
    'name': 'Silverstone',
    'lap_distance_pct': 0.25,
    'current_segment': {
      'name': 'Turn 4',
      'type': 'corner',
      'description': 'Medium-speed right-hander'
    }
  }
  ```

### 4. Tire & Fuel State
- **Purpose**: Vehicle condition and setup data
- **Data**: Tire pressures, temperatures, fuel level
- **Example**:
  ```python
  {
    'tire_pressures': {
      'front_left': 28.5,
      'front_right': 28.3,
      'rear_left': 27.8,
      'rear_right': 27.9
    },
    'fuel': {
      'level': 45.2,
      'level_pct': 75.3
    }
  }
  ```

### 5. Driver Input Trace
- **Purpose**: Time window around the event
- **Data**: 2-second window of driver inputs before/after event
- **Usage**: Shows context of what led to the event

### 6. Lap/Sector Deltas
- **Purpose**: Performance comparison data
- **Data**: Current vs best lap, improvement potential
- **Example**:
  ```python
  {
    'current_lap_time': 85.234,
    'best_lap_time': 84.123,
    'delta_to_best': 1.111,
    'improvement_potential': 1.111
  }
  ```

### 7. Session/Trend History
- **Purpose**: Pattern recognition and trend analysis
- **Data**: Event frequency, trend direction, pattern analysis
- **Example**:
  ```python
  {
    'event_type': 'understeer',
    'total_occurrences': 3,
    'trend_direction': 'worsening',
    'frequency_per_lap': 0.5
  }
  ```

### 8. Setup Baseline
- **Purpose**: Vehicle setup information
- **Data**: Tire pressures, suspension settings, alignment
- **Usage**: Helps AI understand if setup contributes to issues

### 9. AI/ML Anomaly Scores
- **Purpose**: Deviation from ideal patterns
- **Data**: Overall anomaly, technique anomaly scores
- **Example**:
  ```python
  {
    'overall_anomaly': 0.75,
    'technique_anomaly': 0.60
  }
  ```

## Implementation

### Basic Usage

```python
from rich_context_builder import RichContextBuilder, EventContext

# Initialize the builder
builder = RichContextBuilder()

# Add telemetry data to buffer
builder.add_telemetry(telemetry_data)

# Build rich context
event_context = builder.build_rich_context(
    event_type='understeer',
    telemetry_data=telemetry_data,
    context=coaching_context,
    current_segment=track_segment
)

# Format for prompt
prompt_text = builder.format_for_prompt(event_context)
```

### Integration with Coaching System

The rich context is automatically integrated into the coaching system:

1. **Telemetry Processing**: Each telemetry update is added to the rich context buffer
2. **Event Detection**: When coaching insights are generated, rich context is built
3. **AI Prompting**: Rich context is included in AI coaching prompts
4. **Trend Analysis**: Session history is tracked for pattern recognition

### Example Prompt Output

```
=== RICH CONTEXT FOR COACHING ===

EVENT: UNDERSTEER
Location: Turn 4
Timestamp: 1703123456.789

CAR STATE:
- Speed: 95.0 mph
- RPM: 5500
- Gear: 3
- Throttle: 60.0%
- Brake: 20.0%
- Steering: 0.400
- Surface: Asphalt

TRACK STATE:
- Track: Silverstone
- Lap Distance: 25.0%
- Lap: 3
- Session: Practice
- Weather: Clear

TIRE & FUEL STATE:
- Tire Pressures: FL=28.5, FR=28.3, RL=27.8, RR=27.9
- Fuel Level: 75.3%

LAP/SECTOR DELTAS:
- Current Lap: 85.234s
- Best Lap: 84.123s
- Delta to Best: 1.111s
- Improvement Potential: 1.111s

SESSION TRENDS:
- Event Type: understeer
- Total Occurrences: 3
- Recent Occurrences: 2
- Trend Direction: worsening
- Frequency per Lap: 0.50

ANOMALY SCORES:
- Overall Anomaly: 0.750
- Technique Anomaly: 0.600

DRIVER INPUT TRACE (Last 5 samples):
- T0: Speed=95.0, Throttle=60.0%, Brake=20.0%, Steering=0.400
- T1: Speed=93.0, Throttle=55.0%, Brake=25.0%, Steering=0.350
- T2: Speed=91.0, Throttle=50.0%, Brake=30.0%, Steering=0.300
- T3: Speed=89.0, Throttle=45.0%, Brake=35.0%, Steering=0.250
- T4: Speed=87.0, Throttle=40.0%, Brake=40.0%, Steering=0.200

=== END RICH CONTEXT ===
```

## Benefits

### 1. Deeper AI Insights
- **Context**: AI understands not just the event, but the full context
- **Patterns**: Recognizes recurring issues and trends
- **Causality**: Can identify root causes of driving issues

### 2. Personalized Coaching
- **History**: Considers driver's session history and patterns
- **Setup**: Accounts for vehicle setup and conditions
- **Progress**: Tracks improvement over time

### 3. Actionable Advice
- **Specific**: Advice tailored to exact situation and track segment
- **Quantified**: Includes specific numbers and deltas
- **Contextual**: Considers weather, surface, and other factors

### 4. Trend Analysis
- **Patterns**: Identifies recurring issues
- **Progress**: Tracks improvement over sessions
- **Predictive**: Can anticipate issues before they occur

## Configuration

### Rich Context Builder Settings

```python
config = {
    'telemetry_buffer_size': 300,  # 5 seconds at 60Hz
    'event_window_seconds': 2.0,   # Time window around events
    'anomaly_thresholds': {
        'overall': 0.7,
        'technique': 0.6
    }
}

builder = RichContextBuilder(config)
```

### Event Type Mapping

```python
situation_to_event = {
    'insufficient_braking': 'late_braking',
    'early_throttle_in_corners': 'early_throttle',
    'inconsistent_lap_times': 'inconsistency',
    'sector_analysis': 'sector_time_loss',
    'corner_analysis': 'corner_technique',
    'race_strategy': 'strategy',
    'understeer': 'understeer',
    'oversteer': 'oversteer',
    'offtrack': 'offtrack',
    'bad_exit': 'bad_exit',
    'missed_apex': 'missed_apex'
}
```

## Testing

Run the test suite to verify rich context functionality:

```bash
cd coaching-agent
python test_rich_context.py
```

This will test:
- Rich context builder functionality
- Prompt builder integration
- AI coach integration
- Data formatting and structure

## Best Practices

### 1. Event Classification
- Use specific event types for better AI understanding
- Map coaching situations to appropriate event types
- Consider event severity and frequency

### 2. Data Quality
- Ensure telemetry data is accurate and complete
- Validate data ranges and units
- Handle missing or invalid data gracefully

### 3. Performance
- Buffer telemetry efficiently (5-second window)
- Group similar events for better context
- Limit rich context size for API efficiency

### 4. Privacy
- Anonymize sensitive data
- Secure telemetry storage
- Respect user privacy preferences

## Troubleshooting

### Common Issues

1. **Missing Telemetry Data**
   - Check telemetry service connection
   - Verify data field mappings
   - Ensure buffer is being populated

2. **Poor AI Responses**
   - Verify rich context is being included in prompts
   - Check event type classification
   - Review anomaly score calculations

3. **Performance Issues**
   - Monitor buffer size and memory usage
   - Optimize telemetry processing frequency
   - Review API rate limits

### Debug Mode

Enable debug logging to troubleshoot:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Rich context builder will log detailed information
builder = RichContextBuilder()
```

## Future Enhancements

### Planned Features

1. **Machine Learning Integration**
   - Train models on rich context data
   - Predict optimal coaching responses
   - Adaptive anomaly detection

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

The Rich Context system transforms basic telemetry data into comprehensive coaching intelligence. By providing multi-dimensional context to your AI/ML systems, you enable deeper insights, more personalized coaching, and better driver development outcomes.

The system is designed to be:
- **Comprehensive**: Captures all relevant data dimensions
- **Efficient**: Optimized for real-time processing
- **Extensible**: Easy to add new data sources and analysis
- **Reliable**: Robust error handling and fallbacks

Start using rich context today to unlock the full potential of your GT3 AI coaching system! 