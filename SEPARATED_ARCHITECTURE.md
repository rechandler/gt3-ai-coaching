# GT3 AI Coaching - Separated Architecture

## New Architecture Overview

The system now uses a separated architecture with two distinct channels:

### 🚗 Telemetry Server (Port 8081)

- **Purpose**: Pure iRacing telemetry data only
- **Data**: Car speed, temperatures, fuel, lap times, etc.
- **File**: `python-server/telemetry-server.py`
- **WebSocket**: `ws://localhost:8081`

### 🧠 AI Coaching Server (Port 8082)

- **Purpose**: AI-generated coaching messages only
- **Data**: Coaching advice, tips, warnings, analysis
- **File**: `python-server/coaching-server.py`
- **WebSocket**: `ws://localhost:8082`

## Benefits of Separation

### ✅ Clean Architecture

- **Separation of Concerns**: Telemetry ≠ Coaching Logic
- **Independent Scaling**: Each service can be optimized separately
- **Better Debugging**: Issues are isolated to specific channels

### ✅ Consistent Data Flow

- **Pure Telemetry**: Always has car data, never mixed with coaching
- **Reliable Coaching**: Messages have their own delivery guarantee
- **No More Complex Logic**: No need to detect "message changes"

### ✅ Better User Experience

- **Reliable Display**: UI widgets always get the data they expect
- **Real-time Coaching**: Messages arrive independently of telemetry rate
- **Message History**: Coaching server can provide message history

## How It Works

```
┌─────────────────┐    ┌────────────────────┐    ┌─────────────────┐
│    iRacing      │───▶│  Telemetry Server  │───▶│   React UI      │
│    SDK Data     │    │    (Port 8081)     │    │ (Telemetry)     │
└─────────────────┘    └────────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌────────────────────┐    ┌─────────────────┐
                       │  AI Coaching       │───▶│   React UI      │
                       │  Server (8082)     │    │ (Coaching)      │
                       └────────────────────┘    └─────────────────┘
```

1. **Telemetry Server** receives iRacing data and broadcasts pure telemetry
2. **Coaching Server** connects to telemetry server, processes data through AI, sends coaching messages
3. **React UI** connects to both servers independently

## Running the System

### Option 1: Use the batch script

```bash
start-servers.bat
```

### Option 2: Manual start

```bash
# Terminal 1 - Telemetry Server
cd python-server
python telemetry-server.py

# Terminal 2 - Coaching Server
cd python-server
python coaching-server.py

# Terminal 3 - React UI
npm start
```

## UI Changes

The React UI now uses two WebSocket hooks:

- `useIRacingTelemetry()` - Connects to port 8081 for telemetry
- `useCoachingMessages()` - Connects to port 8082 for coaching

The coaching widget now:

- Receives messages directly from coaching server
- Has message history support
- Shows connection status for both telemetry and coaching
- Handles message expiration properly

## Migration Notes

### What Was Removed

- ❌ Coaching fields from telemetry packets (`coachingMessage`, etc.)
- ❌ Complex message change detection logic
- ❌ AI processing mixed with telemetry processing
- ❌ User profile data from telemetry (will be moved to coaching server)

### What Was Added

- ✅ Dedicated coaching server
- ✅ Separate WebSocket connections
- ✅ Message queuing and history
- ✅ Better error handling
- ✅ Independent connection status

## Future Enhancements

With this architecture, we can now easily add:

- **Message Persistence**: Store coaching history in database
- **Multiple AI Models**: Different coaching approaches
- **User Profiles**: Personalized coaching on coaching server
- **Analytics**: Track coaching effectiveness
- **Rate Limiting**: Control message frequency independently
- **Filters**: User can choose message types/priorities

## Troubleshooting

### Telemetry not working

- Check if iRacing is running
- Verify connection to `ws://localhost:8081`
- Check telemetry-server.py logs

### Coaching not working

- Verify connection to `ws://localhost:8082`
- Check if coaching server can connect to telemetry server
- Check coaching-server.py logs

### Both servers running but no data

- Ensure both servers started successfully
- Check Windows firewall settings
- Verify iRacing SDK is installed properly
