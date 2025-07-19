# Micro Analysis System Guide
## Specific, Actionable Feedback with Precise Timing and Speed Deltas

### Overview

The Micro Analysis System provides **gold-standard coaching feedback** with specific, measurable insights like:
- "Braked 0.10s too late"
- "Apex speed 3kph down"
- "Applied throttle 0.15s too early"

This system compares your actual performance against reference data (pro/best lap) and provides precise deltas for timing, speed, and inputs.

### Key Features

#### 1. **Precise Timing Analysis**
- **Brake timing delta**: How early/late you brake compared to reference
- **Throttle timing delta**: When you apply throttle vs. optimal timing
- **Corner entry/exit timing**: Complete corner timing breakdown

#### 2. **Speed Delta Analysis**
- **Entry speed delta**: Speed entering corner vs. reference
- **Apex speed delta**: Speed at corner apex vs. reference
- **Exit speed delta**: Speed exiting corner vs. reference

#### 3. **Input Analysis**
- **Brake pressure delta**: Brake pressure vs. optimal
- **Throttle pressure delta**: Throttle application vs. optimal
- **Steering angle delta**: Steering input vs. optimal line

#### 4. **Pattern Classification**
- **Late/Early apex**: Apex positioning analysis
- **Off-throttle oversteer**: Loss of rear grip detection
- **Understeer**: Front grip loss detection
- **Trail braking**: Brake while steering technique
- **Early/Late throttle**: Throttle timing analysis
- **Inconsistent inputs**: Input smoothness analysis

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telemetry     │───▶│  Micro Analyzer  │───▶│  Coaching       │
│   Data          │    │                  │    │  Feedback       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ Reference Data   │
                       │ Manager          │
                       └──────────────────┘
```

### Components

#### 1. **MicroAnalyzer**
Main analysis engine that processes corner data and generates specific feedback.

#### 2. **ReferenceDataManager**
Manages corner reference data (pro/best lap metrics) for comparison.

#### 3. **PatternClassifier**
Uses ML techniques to classify driving patterns and techniques.

#### 4. **CornerReference**
Data structure containing optimal corner metrics for comparison.

### Usage Examples

#### Basic Integration

```python
from micro_analysis import MicroAnalyzer, ReferenceDataManager

# Initialize
reference_manager = ReferenceDataManager()
micro_analyzer = MicroAnalyzer(reference_manager)

# Process corner data
corner_data = [...]  # Your telemetry data
reference = reference_manager.get_corner_reference("corner_id")

# Analyze
analysis = micro_analyzer.perform_micro_analysis(corner_data, reference)

# Get specific feedback
print(f"Brake timing delta: {analysis.brake_timing_delta:.2f}s")
print(f"Apex speed delta: {analysis.apex_speed_delta:.1f} km/h")
print(f"Specific feedback: {analysis.specific_feedback}")
```

#### Integration with Coaching Agent

```python
from hybrid_coach import HybridCoachingAgent

# Initialize coaching agent (includes micro-analysis)
agent = HybridCoachingAgent(config)

# Process telemetry
telemetry_data = {
    'speed': 120,
    'brake': 60,
    'throttle': 0,
    'steering': 0.3,
    'lap_distance_pct': 0.25,
    'track_name': 'Spa-Francorchamps'
}

# Micro-analysis is automatically processed
agent.process_telemetry(telemetry_data)

# Get insights
insights = agent.get_micro_analysis_insights()
```

### Reference Data Structure

#### CornerReference
```python
@dataclass
class CornerReference:
    corner_id: str
    corner_name: str
    track_name: str
    position_start: float
    position_end: float
    
    # Reference metrics
    reference_brake_point: float      # Lap distance % where braking should start
    reference_brake_pressure: float   # Optimal brake pressure
    reference_entry_speed: float      # Speed entering corner
    reference_apex_speed: float       # Speed at apex
    reference_exit_speed: float       # Speed exiting corner
    reference_throttle_point: float   # Where throttle should be applied
    reference_throttle_pressure: float # Optimal throttle pressure
    reference_steering_angle: float   # Optimal steering angle
    reference_racing_line: List[Tuple[float, float]] # Position, steering pairs
    
    # Timing references
    reference_corner_time: float      # Expected time through corner
    reference_gear: int               # Optimal gear for corner
    
    # Additional context
    corner_type: str                  # 'slow', 'medium', 'high_speed'
    difficulty: str                   # 'easy', 'medium', 'hard'
    notes: str = ""
```

### Analysis Output

#### MicroAnalysis
```python
@dataclass
class MicroAnalysis:
    corner_id: str
    corner_name: str
    
    # Timing deltas (positive = late, negative = early)
    brake_timing_delta: float         # Seconds early/late
    throttle_timing_delta: float      # Seconds early/late
    
    # Speed deltas (positive = faster, negative = slower)
    entry_speed_delta: float          # km/h difference
    apex_speed_delta: float           # km/h difference
    exit_speed_delta: float           # km/h difference
    
    # Input deltas
    brake_pressure_delta: float       # Percentage difference
    throttle_pressure_delta: float    # Percentage difference
    steering_angle_delta: float       # Degrees difference
    
    # Racing line analysis
    racing_line_deviation: float      # Distance from optimal line
    line_smoothness_score: float      # 0-1, higher is smoother
    
    # Time loss analysis
    total_time_loss: float            # Seconds lost in corner
    time_loss_breakdown: Dict[str, float] # Breakdown by factor
    
    # Pattern classification
    detected_patterns: List[str]      # e.g., "late_apex", "off_throttle_oversteer"
    pattern_confidence: Dict[str, float] # Confidence scores for patterns
    
    # Specific feedback
    specific_feedback: List[str]      # Actionable advice
    priority: str                     # 'critical', 'high', 'medium', 'low'
```

### Feedback Examples

#### Poor Technique
```
📉 POOR TECHNIQUE ANALYSIS
============================================================
Corner: Eau Rouge
Total time loss: 0.22s
Brake timing delta: 0.00s
Throttle timing delta: -0.07s
Apex speed delta: -7.0 km/h
Detected patterns: ['early_apex', 'trail_braking', 'late_throttle', 'inconsistent_inputs']
Priority: high

Specific feedback:
  • 🚀 Applied throttle 0.07s too late
  • ⚡ Apex speed 7.0km/h down
  • 🏁 Exit speed 5.0km/h down
  • 🔄 Apex too early - turn in later
  • 🛑 Trail braking detected - good technique!
  • 🚀 Throttle too late - apply earlier
  • 📊 Inconsistent inputs - smooth out your driving
```

#### Good Technique
```
📈 GOOD TECHNIQUE ANALYSIS
============================================================
Corner: Eau Rouge
Total time loss: 0.06s
Brake timing delta: 0.00s
Throttle timing delta: -0.07s
Apex speed delta: 0.0 km/h
Detected patterns: ['early_apex', 'trail_braking', 'late_throttle', 'inconsistent_inputs']
Priority: high

Specific feedback:
  • 🚀 Applied throttle 0.07s too late
  • 🏁 Exit speed 5.0km/h up (good!)
  • 🔄 Apex too early - turn in later
  • 🛑 Trail braking detected - good technique!
  • 🚀 Throttle too late - apply earlier
  • 📊 Inconsistent inputs - smooth out your driving
```

### Pattern Classification

The system detects various driving patterns:

#### 1. **Late/Early Apex**
- **Late Apex**: Apex occurs after optimal point
- **Early Apex**: Apex occurs before optimal point
- **Impact**: Affects corner exit speed and line

#### 2. **Off-Throttle Oversteer**
- **Detection**: High yaw rate with low throttle
- **Cause**: Loss of rear grip during corner entry
- **Solution**: Smoother inputs, better weight transfer

#### 3. **Understeer**
- **Detection**: High steering angle with low yaw rate
- **Cause**: Loss of front grip
- **Solution**: Reduce steering input, adjust line

#### 4. **Trail Braking**
- **Detection**: Brake pressure while steering
- **Assessment**: Good technique when done correctly
- **Feedback**: Positive reinforcement

#### 5. **Early/Late Throttle**
- **Early Throttle**: Applied before apex
- **Late Throttle**: Applied after optimal point
- **Impact**: Affects corner exit speed

#### 6. **Inconsistent Inputs**
- **Detection**: High variance in throttle/brake/steering
- **Impact**: Reduces corner consistency
- **Solution**: Smooth out inputs

### Time Loss Calculation

The system calculates time loss from various factors:

```python
time_loss = (
    abs(brake_timing_delta) * 0.1 +      # 0.1s per 0.1s timing error
    abs(throttle_timing_delta) * 0.1 +   # 0.1s per 0.1s timing error
    abs(entry_speed_delta) * 0.01 +      # 0.01s per km/h
    abs(apex_speed_delta) * 0.02 +       # 0.02s per km/h (critical)
    abs(exit_speed_delta) * 0.01         # 0.01s per km/h
)
```

### Reference Data Management

#### Creating References
```python
# From best lap data
reference = reference_manager.create_reference_from_best_lap(
    corner_id="spa_eau_rouge",
    corner_data=best_lap_corner_data
)

# Manual creation
reference = CornerReference(
    corner_id="spa_eau_rouge",
    corner_name="Eau Rouge",
    track_name="Spa-Francorchamps",
    position_start=0.03,
    position_end=0.08,
    reference_brake_point=0.035,
    reference_brake_pressure=70.0,
    reference_entry_speed=140.0,
    reference_apex_speed=95.0,
    reference_exit_speed=135.0,
    reference_throttle_point=0.065,
    reference_throttle_pressure=85.0,
    reference_steering_angle=0.4,
    reference_racing_line=[...],
    reference_corner_time=4.2,
    reference_gear=4,
    corner_type="high_speed",
    difficulty="hard"
)
```

#### Loading References
```python
# Load from file
reference_manager.load_references()

# Get specific reference
reference = reference_manager.get_corner_reference("spa_eau_rouge")

# Save references
reference_manager.save_references()
```

### Integration with Visualization

The micro-analysis data can be used for:

#### 1. **Real-time Overlays**
- Show timing deltas on screen
- Display speed comparisons
- Highlight pattern classifications

#### 2. **Post-session Analysis**
- Corner-by-corner breakdown
- Time loss analysis
- Pattern frequency analysis

#### 3. **Progress Tracking**
- Track improvements over time
- Compare against personal bests
- Identify recurring issues

### Configuration

#### Pattern Thresholds
```python
pattern_thresholds = {
    'late_apex': 0.1,              # 10% later than reference
    'early_apex': -0.1,            # 10% earlier than reference
    'off_throttle_oversteer': 0.3, # High yaw rate with low throttle
    'understeer': 0.8,             # High steering with low yaw rate
    'trail_braking': 0.2,          # Brake pressure while steering
    'early_throttle': 0.15,        # Throttle before apex
    'late_throttle': -0.15,        # Throttle after apex
    'inconsistent_inputs': 0.25,   # High variance in inputs
}
```

#### Priority Mapping
```python
priority_map = {
    'critical': 0.9,  # Safety issues, major time loss
    'high': 0.7,      # Significant time loss
    'medium': 0.5,    # Moderate improvements
    'low': 0.3        # Minor optimizations
}
```

### Best Practices

#### 1. **Reference Data Quality**
- Use pro-level reference data when available
- Update references with personal bests
- Validate reference data accuracy

#### 2. **Feedback Timing**
- Provide feedback immediately after corner completion
- Avoid overwhelming with too many details
- Focus on highest priority issues

#### 3. **Pattern Recognition**
- Track pattern frequency over time
- Identify recurring issues
- Provide targeted training recommendations

#### 4. **Integration**
- Combine with LLM for contextual advice
- Use in visualization overlays
- Include in post-session reports

### Future Enhancements

#### 1. **ML Pattern Recognition**
- Train models on large datasets
- Improve pattern detection accuracy
- Add new pattern types

#### 2. **Advanced Analytics**
- Corner difficulty assessment
- Weather condition adjustments
- Tire wear considerations

#### 3. **Personalization**
- Adaptive thresholds based on skill level
- Personalized feedback style
- Learning from user preferences

### Conclusion

The Micro Analysis System provides the **gold standard** for racing coaching feedback with:
- **Precise measurements** (0.1s timing, 1km/h speed deltas)
- **Specific feedback** ("braked 0.10s too late")
- **Pattern classification** (late apex, off-throttle oversteer)
- **Time loss analysis** (total and breakdown)
- **Actionable advice** (immediate improvements)

This system transforms generic coaching into specific, measurable, and actionable feedback that drivers can immediately apply to improve their performance. 