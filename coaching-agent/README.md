# GT3 AI Coaching Agent

A sophisticated hybrid coaching system that combines local machine learning with remote AI to provide real-time driving coaching for GT3 racing simulations.

## Overview

The Hybrid Coaching Agent analyzes telemetry data in real-time and provides coaching feedback through two complementary approaches:

- **Local ML Coach**: Fast, lightweight pattern recognition for immediate feedback
- **Remote AI Coach**: Sophisticated natural language coaching using OpenAI API for complex situations

## Architecture

```
coaching-agent/
├── coaching_data_service.py   # Connects to telemetry service, runs agent, serves UI
├── hybrid_coach.py            # Main orchestrator
├── local_ml_coach.py          # Local ML analysis
├── remote_ai_coach.py         # OpenAI integration
├── message_queue.py           # Message prioritization
├── telemetry_analyzer.py      # Telemetry processing
├── session_manager.py         # Session tracking
├── config.py                  # Configuration management
├── main.py                    # Startup script
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

## How It Works

- **Coaching Data Service** (`coaching_data_service.py`):
  - Connects to the telemetry service's WebSocket endpoints (9001/9002)
  - Receives real-time telemetry and session data
  - Passes data to the Hybrid Coaching Agent for analysis
  - Forwards coaching messages and processed data to the UI (via its own WebSocket server)
- **Hybrid Coaching Agent** (`hybrid_coach.py`):
  - Analyzes telemetry using local ML and remote AI
  - Generates actionable coaching messages

## Features

### Local ML Coach

- Real-time pattern detection
- Braking analysis
- Cornering technique assessment
- Consistency monitoring
- Lightweight heuristic-based coaching

### Remote AI Coach

- Natural language coaching messages
- Contextual situation analysis
- Strategic advice
- Rate-limited to preserve API usage
- Sophisticated prompt engineering

### Message Queue System

- Priority-based message delivery
- Duplicate message filtering
- Category-specific cooldowns
- Configurable delivery rates

### Telemetry Analysis

- Motion calculations (G-forces)
- Sector performance analysis
- Corner detection and analysis
- Performance trend tracking

### Session Management

- Persistent session storage
- Performance metrics tracking
- Progress monitoring
- Export capabilities

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up OpenAI API key (optional):

```bash
export OPENAI_API_KEY="your-api-key-here"
```

3. Create configuration file:

```bash
python config.py
```

## Configuration

The system uses a hierarchical configuration system with these main sections:

### Coaching Modes

- **Beginner**: More frequent, encouraging messages
- **Intermediate**: Balanced technical advice
- **Advanced**: Detailed, technical feedback
- **Race**: Minimal, critical-only messages

### Local Config

```json
{
  "local_config": {
    "confidence_threshold": 0.7,
    "pattern_detection_sensitivity": 0.8,
    "message_cooldown": 8.0
  }
}
```

### Remote Config

```json
{
  "remote_config": {
    "api_key": "your-openai-api-key",
    "model": "gpt-3.5-turbo",
    "max_requests_per_minute": 5
  }
}
```

## Usage

### Start the Coaching Agent and Data Service

```bash
python main.py
```
This will start both the coaching agent and the coaching data service, which will connect to the telemetry service and serve coaching messages to the UI.

### With Simulation

```bash
python main.py --simulate
```

### Production Mode

```bash
python main.py --environment production
```

### Custom Configuration

```bash
python main.py --config my_config.json
```

## API Integration

### Processing Telemetry

```python
from hybrid_coach import HybridCoachingAgent

agent = HybridCoachingAgent(config)
await agent.start()

# Process telemetry data
telemetry_data = {
    'speed': 120,
    'brake_pct': 30,
    'throttle_pct': 80,
    'steering_angle': 0.2,
    'lap_distance_pct': 0.3
}

await agent.process_telemetry(telemetry_data)
```

### Getting Statistics

```python
stats = agent.get_stats()
print(f"Messages delivered: {stats['total_messages']}")
print(f"AI usage rate: {stats['ai_usage_rate']}")
```

## Message Categories

The system categorizes coaching messages for intelligent filtering:

- **Braking**: Brake pressure, timing, technique
- **Cornering**: Racing line, apex, technique
- **Throttle**: Application timing, modulation
- **Consistency**: Lap time variation, repeatability
- **Safety**: Immediate safety concerns
- **Strategy**: Race tactics, tire/fuel management

## Decision Engine

The hybrid system intelligently decides when to use local vs. remote coaching:

- **Use Local**: High confidence, low importance, frequent situations
- **Use Remote**: Complex analysis, low confidence, strategic advice
- **Rate Limiting**: Respects API limits and user preferences

## Performance Features

### Pattern Detection

- Late/early braking detection
- Cornering technique analysis
- Throttle application patterns
- Consistency monitoring

### Analysis Capabilities

- G-force calculations
- Sector time analysis
- Corner performance assessment
- Racing line evaluation

### Session Tracking

- Lap time progression
- Performance metrics
- Improvement tracking
- Historical analysis

## Coaching Examples

### Local ML Messages

- "Brake earlier for turn 1. You're braking 100m too late."
- "You can get on throttle earlier in turn 3."
- "Focus on consistency - your lap times vary by 0.8s."

### AI-Generated Messages

- "Your exit speed through the chicane is costing time. Try a later apex to maximize acceleration onto the back straight."
- "Consider a more aggressive line through sector 2 - you're being too conservative in the medium-speed corners."

## Extensibility

The system is designed for easy extension:

### Adding New Patterns

```python
def detect_custom_pattern(self, telemetry_data):
    # Custom pattern detection logic
    return patterns
```

### Custom Message Templates

```python
CUSTOM_TEMPLATES = {
    'my_category': {
        'my_pattern': "Custom coaching message for {situation}"
    }
}
```

### Track-Specific Configuration

```python
TRACK_CONFIGS['my_track'] = {
    'sector_boundaries': [0.0, 0.35, 0.70, 1.0],
    'key_corners': {...}
}
```

## Logging and Debugging

The system provides comprehensive logging:

```bash
# Enable debug logging
python main.py --debug

# View logs
tail -f coaching_agent.log
```

## Integration with Telemetry Service

The coaching agent (via the coaching data service) connects to the telemetry service's WebSocket endpoints:
- `ws://localhost:9001` (telemetry data)
- `ws://localhost:9002` (session/driver data)

It processes incoming data and provides coaching messages to the UI or other consumers.

## Future Enhancements

- Machine learning model training from session data
- Advanced setup recommendations
- Predictive analysis for race strategy
- Integration with car setup tools
- Multiplayer coaching scenarios

## Troubleshooting

### Common Issues

1. **No AI coaching**: Check OpenAI API key configuration
2. **High message frequency**: Adjust cooldown settings
3. **Performance issues**: Reduce telemetry buffer size
4. **Missing dependencies**: Run `pip install -r requirements.txt`

### Debug Mode

```bash
python main.py --debug --simulate
```

This will provide detailed logging of all coaching decisions and message processing.

## License

This project is part of the GT3 AI Coaching system and follows the same licensing terms as the main project.
