# GT3 AI Coaching - Port Architecture

## 🏗️ Proper Separation of Concerns

The GT3 AI Coaching system follows a clean microservices architecture with proper separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   iRacing SDK   │───▶│ Telemetry       │───▶│ Coaching Data   │───▶ UI (React)
│                 │    │ Service         │    │ Service         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              │                        │
                       Port 9001 & 9002         Port 8082
```

## 📡 Port Assignments

### Telemetry Service (Raw Data Provider)

- **Port 9001**: Real-time telemetry stream
  - Speed, RPM, gear, throttle, brake
  - Lap times, delta times
  - Position, acceleration data
  - Updates: ~60Hz (real-time)
- **Port 9002**: Session/track data stream
  - Track name, car name, session info
  - Driver information
  - Weather, track conditions
  - Updates: On session change

### Coaching Data Service (Intelligence Layer)

- **Port 8082**: UI client interface
  - Processed telemetry data
  - AI coaching messages
  - Session management
  - Analytics and insights

## 🔌 Connection Flow

### ✅ Correct Architecture

```
React UI ──────────────────▶ Coaching Service (8082)
                                     │
                                     ├─▶ Telemetry Stream (9001)
                                     └─▶ Session Stream (9002)
                                            │
                                    Telemetry Service
                                            │
                                       iRacing SDK
```

### ❌ Incorrect (What We Fixed)

```
React UI ──────────────────▶ Telemetry Service (9001/9002)
                                     │
                               Direct connection
                                     │
                                iRacing SDK
```

## 🎯 Benefits of This Architecture

1. **Separation of Concerns**

   - Telemetry Service: Pure data collection
   - Coaching Service: Intelligence and processing
   - UI: Presentation only

2. **Scalability**

   - Multiple coaching services can connect to one telemetry service
   - Multiple UIs can connect to one coaching service
   - Services can be on different machines

3. **Maintainability**

   - Each service has single responsibility
   - Changes to coaching logic don't affect telemetry
   - UI changes don't affect backend services

4. **Performance**
   - Raw telemetry stays on fast internal ports
   - Only processed data sent to UI
   - Coaching calculations don't block telemetry

## 🔧 Configuration

### Current Setup (Correct)

- **Telemetry Service**: Ports 9001 (telemetry) + 9002 (session)
- **Coaching Service**: Port 8082 (UI clients)
- **React UI**: Connects only to port 8082

### Service Dependencies

```yaml
Telemetry Service:
  - Depends on: iRacing SDK
  - Exposes: 9001, 9002
  - Clients: Coaching services

Coaching Service:
  - Depends on: Telemetry Service (9001, 9002)
  - Exposes: 8082
  - Clients: UI applications

React UI:
  - Depends on: Coaching Service (8082)
  - Exposes: N/A (client only)
  - Clients: End users
```

## 🚀 Starting Services (Correct Order)

1. **Start Telemetry Service** (ports 9001, 9002)

   ```bash
   cd telemetry-server
   python services/telemetry_service.py
   ```

2. **Start Coaching Service** (port 8082)

   ```bash
   cd telemetry-server
   python services/coaching_data_service.py
   ```

3. **Start React UI**
   ```bash
   npm start  # Connects to localhost:8082
   ```

## 🔍 Debugging Connections

Test each layer independently:

```bash
# Test telemetry service directly
python debug-telemetry-direct.py    # Tests ports 9001, 9002

# Test coaching service
python debug-connection.py          # Tests port 8082

# Test UI connection
# Open browser dev tools, check WebSocket connections
```
