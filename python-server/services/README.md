# GT3 AI Coaching - Services Module

This directory contains the modular services that make up the GT3 AI coaching platform.

## Architecture

The platform is now split into focused, single-responsibility services:

```
iRacing SDK → Telemetry Service → Coaching Data Service → React UI
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

- **Purpose**: Process telemetry and manage coaching sessions
- **Responsibilities**:
  - Receive data from telemetry service
  - Process telemetry for coaching insights
  - Maintain session state and persistence
  - Forward processed data to UI
- **Ports**:
  - `8082`: UI interface (WebSocket)

### 3. Service Launcher (`launcher.py`)

- **Purpose**: Start and coordinate all services
- **Modes**:
  - Single-process (default, easier for development)
  - Multi-process (better isolation)

## Usage

### Start All Services

```bash
cd python-server/services
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

This replaces the previous monolithic `telemetry-server.py` which tried to handle:

- iRacing SDK connection
- Telemetry processing
- Session management
- UI communication
- Data persistence

Now each concern is handled by a dedicated service with clear interfaces.
