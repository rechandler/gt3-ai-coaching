# Architecture Migration - July 2025

## Migration from Monolithic to Modular Architecture

### What Changed

The GT3 AI Coaching system has been migrated from a monolithic architecture to a modular, service-based architecture:

#### Before (Removed)
- `python-server/` - Monolithic directory containing:
  - `telemetry-server.py` - Single large file handling telemetry + UI + coaching
  - `coaching-server.py` - Separate coaching server
  - Various AI coaching implementations

#### After (Current)
- `telemetry-server/services/` - Modular service architecture:
  - `telemetry_service.py` - Pure iRacing SDK interface
  - `coaching_data_service.py` - Data processing + coaching integration
  - `launcher.py` - Service coordination
- `coaching-agent/` - Hybrid coaching agent:
  - `hybrid_coach.py` - Main coaching orchestrator
  - `local_ml_coach.py` - Fast local ML patterns
  - `remote_ai_coach.py` - Advanced AI coaching
  - `message_queue.py` - Intelligent message delivery

### Benefits of New Architecture

1. **Separation of Concerns**: Each service has a single, clear responsibility
2. **Modularity**: Services can be developed, tested, and deployed independently  
3. **Scalability**: Services can be distributed across multiple machines
4. **Reliability**: If one service fails, others continue running
5. **Debugging**: Much easier to isolate and fix issues
6. **Testing**: Each service can be tested in isolation

### Data Flow

```
iRacing SDK → Telemetry Service → Coaching Data Service (+ Hybrid Agent) → React UI
```

### Port Configuration

- **9001**: Telemetry data stream (60Hz)
- **9002**: Session/driver data stream (5s intervals)  
- **8082**: UI interface + coaching messages

### Legacy Documentation Preserved

- `docs/Legacy_LLM_Integration_Guide.md` - Previous LLM integration approach
- `docs/Legacy_Cloud_Setup_Guide.md` - Previous cloud deployment guide

### Startup Scripts Updated

- `start-servers.bat` - Updated to use new service architecture
- `start-server.bat` - Updated to start coaching data service

### Migration Date

**July 14, 2025** - Successfully migrated and tested with GT3 overlay integration.
