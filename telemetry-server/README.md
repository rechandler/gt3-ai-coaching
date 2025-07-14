# GT3 AI Coaching - Telemetry Server

This directory contains the new modular telemetry server architecture for the GT3 AI coaching platform, now integrated with the Hybrid Coaching Agent.

## Architecture

The new telemetry server integrates AI coaching directly into the data pipeline:

```
iRacing SDK → Telemetry Service → Coaching Data Service (+ AI Coach) → React UI
```

## Features

### Core Telemetry Services
- **Real-time telemetry streaming** from iRacing SDK
- **Session and driver data** collection
- **Modular service architecture** for reliability

### AI Coaching Integration
- **Hybrid Coaching Agent** processes telemetry in real-time
- **Local ML patterns** provide instant feedback
- **Remote AI coaching** for sophisticated analysis
- **Intelligent message delivery** with priority queuing

## Directory Structure

```
telemetry-server/
├── services/
│   ├── telemetry_service.py         # Core iRacing SDK interface
│   ├── coaching_data_service.py     # Data processing + AI coaching
│   ├── mock_irsdk.py                # Mock SDK for testing
│   ├── launcher.py                  # Service coordination
│   └── __init__.py                  # Package initialization
├── test_coaching_integration.py     # Integration testing
├── start-telemetry-with-coaching.bat # Enhanced startup script
├── README.md                        # This file
└── requirements.txt                 # Python dependencies
```

## Services

### 1. Telemetry Service (`telemetry_service.py`)

- **Purpose**: Direct interface to iRacing SDK
- **Responsibilities**:
  - Connect to iRacing SDK (iRSDK)
  - Collect real-time telemetry data
  - Collect session/driver information
  - Stream data via WebSocket
- **Ports**:
  - `9001`: Telemetry data stream (60Hz)
  - `9002`: Session/driver data stream (5s intervals)

### 2. Coaching Data Service (`coaching_data_service.py`)

- **Purpose**: Process telemetry and manage coaching sessions with AI integration
- **Responsibilities**:
  - Receive data from telemetry service
  - Process telemetry through the Hybrid Coaching Agent
  - Generate real-time coaching messages
  - Maintain session state and persistence
  - Forward processed data and coaching to UI
- **Ports**:
  - `8082`: UI interface (WebSocket)
- **AI Features**:
  - Automatic coaching agent initialization
  - Real-time telemetry processing through ML/AI
  - Coaching message prioritization and delivery
  - Coaching mode control via UI
  - Performance statistics and monitoring

## Quick Start

### With AI Coaching (Recommended)

1. **Ensure coaching agent is available**:
   ```bash
   # The coaching-agent directory should exist at ../coaching-agent/
   ls ../coaching-agent/hybrid_coach.py
   ```

2. **Start with coaching integration**:
   ```bash
   # Windows
   start-telemetry-with-coaching.bat
   
   # Or manually
   cd telemetry-server
   pip install -r requirements.txt
   pip install -r ../coaching-agent/requirements.txt
   python services/launcher.py
   ```

### Without AI Coaching

1. **Start basic telemetry services**:
   ```bash
   cd telemetry-server
   pip install -r requirements.txt
   python services/launcher.py
   ```

## Integration Testing

Test the coaching integration:

```bash
# Start the telemetry server first
python services/launcher.py

# In another terminal, run the integration test
python test_coaching_integration.py
```

## Service Endpoints

### Telemetry Service
- **Telemetry Stream**: `ws://localhost:9001`
  - Real-time telemetry data (60Hz)
- **Session Stream**: `ws://localhost:9002`
  - Session/driver information (5s intervals)

### Coaching Data Service  
- **UI Interface**: `ws://localhost:8082`
  - Processed telemetry data
  - Coaching messages
  - Service status and control

## Coaching Message Format

The coaching data service delivers AI coaching messages in this format:

```json
{
  "type": "coaching_message",
  "data": {
    "content": "Brake earlier for turn 1 - you're 100ms late",
    "category": "braking",
    "priority": "HIGH", 
    "source": "local_ml",
    "confidence": 0.85,
    "context": "corner_entry",
    "timestamp": 1640995200.123
  },
  "timestamp": 1640995200.123
}
```

## Coaching Control Commands

Send these commands to the UI interface for coaching control:

### Get Status
```json
{
  "type": "getStatus"
}
```

### Set Coaching Mode
```json
{
  "type": "setCoachingMode",
  "mode": "intermediate"  // beginner, intermediate, advanced, race
}
```

### Get Coaching Statistics
```json
{
  "type": "getCoachingStats"
}
```

## Configuration

### Coaching Agent Setup

The coaching agent is automatically detected and initialized if available. Configuration is managed through:

- `../coaching-agent/coaching_config.json` - Main coaching configuration
- Environment variables for API keys (OPENAI_API_KEY)

### Service Configuration

Modify service parameters in `launcher.py`:

```python
# Telemetry Service ports
telemetry_port=9001  # Telemetry stream
session_port=9002    # Session stream

# Coaching Data Service port  
ui_port=8082         # UI interface
```

## Troubleshooting

### Common Issues

1. **Coaching agent not available**:
   - Ensure `../coaching-agent/` directory exists
   - Install coaching dependencies: `pip install -r ../coaching-agent/requirements.txt`

2. **No coaching messages**:
   - Check if iRacing is running and generating telemetry
   - Verify coaching agent is active in status response
   - Some coaching triggers require specific driving patterns

3. **Connection issues**:
   - Ensure no other services are using the ports
   - Check firewall settings
   - Verify all dependencies are installed

### Debug Mode

Enable debug logging:

```python
# In launcher.py, change logging level
logging.basicConfig(level=logging.DEBUG)
```

### Service Status

Monitor service health:
- Service logs show connection status every 30 seconds
- UI status command shows all service states
- Integration test validates full pipeline

## Architecture Benefits

### Modular Design
- **Independent services** can be restarted separately
- **Focused responsibilities** make debugging easier
- **Scalable architecture** allows adding new services

### AI Integration
- **Real-time processing** provides immediate coaching
- **Intelligent message filtering** prevents information overload
- **Adaptive coaching** adjusts to driver skill and preferences
- **Local + Remote AI** optimizes performance and cost

### Development Features
- **Mock iRacing SDK** enables development without simulator
- **Integration testing** validates end-to-end functionality
- **Comprehensive logging** aids debugging and monitoring

### 3. Service Launcher (`launcher.py`)

- **Purpose**: Start and coordinate all services
- **Modes**:
  - Single-process (default, easier for development)
  - Multi-process (better isolation)

## Usage

### Start All Services

```bash
cd telemetry-server/services
python launcher.py
```

### Start Individual Services

```bash
# Telemetry service only
python telemetry_service.py

# Coaching data service only (requires telemetry service running)
python coaching_data_service.py
```

## Data Flow

1. **iRacing SDK** → Raw telemetry and session data
2. **Telemetry Service** → Clean, structured data streams
3. **Coaching Data Service** → Processed data with coaching insights
4. **React UI** → Displays coaching information

## Benefits of This Architecture

- **Separation of Concerns**: Each service has a single, clear responsibility
- **Modularity**: Services can be developed, tested, and deployed independently
- **Scalability**: Services can be distributed across multiple machines
- **Reliability**: If one service fails, others continue running
- **Debugging**: Much easier to isolate and fix issues
- **Testing**: Each service can be tested in isolation

## Migration from Monolithic Design

This replaces the previous monolithic `python-server/telemetry-server.py` which tried to handle:

- iRacing SDK connection
- Telemetry processing
- Session management
- UI communication
- Data persistence

Now each concern is handled by a dedicated service with clear interfaces.

## Connection to React UI

Update your React application to connect to the new coaching data service:

```javascript
// Old connection (monolithic)
const ws = new WebSocket("ws://localhost:8081");

// New connection (modular)
const ws = new WebSocket("ws://localhost:8082");
```

The message format remains compatible with your existing React UI code.
