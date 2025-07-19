# GT3 AI Coaching - Telemetry Server

This directory contains the modular telemetry server architecture for the GT3 AI coaching platform.

## Architecture

The telemetry server provides real-time telemetry and session data streams:

```
iRacing SDK → Telemetry Service → React UI
```

## Features

### Core Telemetry Services

- Real-time telemetry streaming from iRacing SDK
- Session and driver data collection
- Modular service architecture for reliability

## Directory Structure

```
telemetry-server/
├── services/
│   ├── telemetry_service.py         # Core iRacing SDK interface
│   ├── mock_irsdk.py                # Mock SDK for testing
│   └── __init__.py                  # Package initialization
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
```

## Services

### Telemetry Service (`telemetry_service.py`)

- **Purpose**: Direct interface to iRacing SDK
- **Responsibilities**:
  - Connect to iRacing SDK (iRSDK)
  - Collect real-time telemetry data
  - Collect session/driver information
  - Stream data via WebSocket
- **Ports**:
  - `9001`: Telemetry data stream (60Hz)
  - `9002`: Session/driver data stream (5s intervals)

## Quick Start

1. **Start all services from the project root**:
   ```bash
   start-all-services.bat
   ```
   This will launch the telemetry service and coaching agent in separate windows.

## Service Endpoints

### Telemetry Service

- **Telemetry Stream**: `ws://localhost:9001`
  - Real-time telemetry data (60Hz)
- **Session Stream**: `ws://localhost:9002`
  - Session/driver information (5s intervals)

## Configuration

### Service Configuration

Modify service parameters in `services/telemetry_service.py` if needed:

```python
# Telemetry Service ports
telemetry_port=9001  # Telemetry stream
session_port=9002    # Session stream
```

## Troubleshooting

### Common Issues

1. **No telemetry data**:
   - Check if iRacing is running and generating telemetry
   - Ensure no other services are using the ports
   - Check firewall settings
   - Verify all dependencies are installed

### Debug Mode

Enable debug logging:

```python
# In telemetry_service.py, change logging level
logging.basicConfig(level=logging.DEBUG)
```

## Usage

### Start All Services

```bash
start-all-services.bat
```

### Start Telemetry Service Only (for development)

```bash
cd telemetry-server/services
python telemetry_service.py
```

## Data Flow

1. **iRacing SDK** → Raw telemetry and session data
2. **Telemetry Service** → Clean, structured data streams
3. **React UI** → Displays telemetry information

## Benefits of This Architecture

- **Separation of Concerns**: Each service has a single, clear responsibility
- **Modularity**: Services can be developed, tested, and deployed independently
- **Scalability**: Services can be distributed across multiple machines
- **Reliability**: If one service fails, others continue running
- **Debugging**: Much easier to isolate and fix issues
- **Testing**: Each service can be tested in isolation
