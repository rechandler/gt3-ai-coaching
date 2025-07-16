"""
Coaching Data Service
====================

This service handles:
1. Receiving telemetry and session data from the telemetry service
2. Processing telemetry for coaching insights via the Hybrid Coaching Agent
3. Maintaining session persistence 
4. Forwarding processed data and coaching messages to the coaching UI

This service acts as the bridge between raw telemetry and the AI coaching platform.
"""

import asyncio
import json
import logging
import time
import websockets
import websockets.exceptions
import sys
import os
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Add coaching-agent to path
# Get the directory where this file lives (which is coaching-agent/)
project_root = os.path.dirname(os.path.abspath(__file__))
coaching_agent_path = project_root

logger.info(f"Looking for coaching agent at: {coaching_agent_path}")

if os.path.exists(coaching_agent_path):
    sys.path.insert(0, coaching_agent_path)
    
    try:
        from hybrid_coach import HybridCoachingAgent
        from config import ConfigManager
        COACHING_AGENT_AVAILABLE = True
        logger.info("Coaching agent imported successfully")
    except ImportError as e:
        logger.warning(f"Failed to import coaching agent: {e}")
        COACHING_AGENT_AVAILABLE = False
else:
    logger.warning(f"Coaching agent directory not found at: {coaching_agent_path}")
    COACHING_AGENT_AVAILABLE = False

@dataclass
class SessionState:
    """Track current session state"""
    track_name: str = "Unknown Track"
    car_name: str = "Unknown Car"
    session_start_time: Optional[float] = None
    last_update_time: Optional[float] = None
    is_active: bool = False

class CoachingDataService:
    """
    Service for processing telemetry data and managing coaching sessions.
    
    Responsibilities:
    - Connect to telemetry service streams
    - Process telemetry for coaching insights
    - Maintain session state and persistence
    - Forward data to coaching UI
    """
    
    def __init__(
        self, 
        telemetry_host: str = "localhost",
        telemetry_port: int = 9001,
        session_port: int = 9002,
        ui_host: str = "localhost", 
        ui_port: int = 8082
    ):
        self.telemetry_host = telemetry_host
        self.telemetry_port = telemetry_port
        self.session_port = session_port
        self.ui_host = ui_host
        self.ui_port = ui_port
        
        # UI client connections
        self.ui_clients: Set = set()
        
        # Service state
        self.session_state = SessionState()
        self.telemetry_connected = False
        self.session_connected = False
        
        # Data storage
        self.latest_telemetry = {}
        self.latest_session_data = {}
        
        # Connection objects
        self.telemetry_websocket = None
        self.session_websocket = None
        
        # Initialize Coaching Agent
        self.coaching_agent = None
        self.coaching_agent_active = False
        if COACHING_AGENT_AVAILABLE:
            self._initialize_coaching_agent()
    
    def _initialize_coaching_agent(self):
        """Initialize the hybrid coaching agent"""
        try:
            # Load coaching configuration
            config_manager = ConfigManager()
            coaching_config = config_manager.get_config()
            
            # Create the coaching agent
            self.coaching_agent = HybridCoachingAgent(coaching_config)
            logger.info("Coaching agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize coaching agent: {e}")
            self.coaching_agent = None
    
    async def start_coaching_agent(self):
        """Start the coaching agent"""
        if self.coaching_agent and not self.coaching_agent_active:
            try:
                # Start the coaching agent in the background
                asyncio.create_task(self.coaching_agent.start())
                self.coaching_agent_active = True
                logger.info("Coaching agent started successfully")
            except Exception as e:
                logger.error(f"Failed to start coaching agent: {e}")
                self.coaching_agent_active = False
    
    async def stop_coaching_agent(self):
        """Stop the coaching agent"""
        if self.coaching_agent and self.coaching_agent_active:
            try:
                await self.coaching_agent.stop()
                self.coaching_agent_active = False
                logger.info("Coaching agent stopped")
            except Exception as e:
                logger.error(f"Failed to stop coaching agent: {e}")
        return None
    
    async def process_telemetry_with_coaching(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process telemetry through the coaching agent and return enhanced data"""
        enhanced_data = telemetry_data.copy()
        
        if self.coaching_agent and self.coaching_agent_active:
            try:
                # Transform telemetry to coaching agent format
                coaching_telemetry = self._transform_telemetry_for_coaching(telemetry_data)
                
                # Process through coaching agent (this may generate messages)
                await self.coaching_agent.process_telemetry(coaching_telemetry)
                
                # Check for new coaching messages and send to UI
                await self._check_for_coaching_messages()
                
                # Add coaching agent stats to the data
                try:
                    coaching_stats = self.coaching_agent.get_stats()
                    enhanced_data['coaching_stats'] = coaching_stats
                except Exception as e:
                    logger.debug(f"Could not get coaching stats: {e}")
                    enhanced_data['coaching_stats'] = {"status": "active"}
                
            except Exception as e:
                logger.error(f"Error processing telemetry with coaching agent: {e}")
        
        return enhanced_data
    
    async def _check_for_coaching_messages(self):
        """Check for new coaching messages and forward them to UI"""
        if not (self.coaching_agent and self.coaching_agent_active):
            return
            
        try:
            # Get the next coaching message from the agent's queue
            message = await self.coaching_agent.message_queue.get_next_message()
            
            if message:
                # Format message for UI - using the format expected by React overlay
                coaching_message = {
                    "type": "coaching",
                    "id": f"{int(message.timestamp * 1000)}_{message.category}",
                    "data": {
                        "message": message.content,
                        "category": message.category,
                        "priority": self._map_priority_to_number(message.priority),
                        "confidence": int(message.confidence * 100),
                        "source": message.source,
                        "context": message.context,
                        "secondary_messages": [],
                        "improvement_potential": None
                    },
                    "timestamp": message.timestamp
                }
                
                # Send to UI clients
                await self.broadcast_to_ui(coaching_message)
                
                # Log the coaching message
                logger.info(f"Coaching: [{message.category}] {message.content}")
                
        except Exception as e:
            logger.error(f"Error checking for coaching messages: {e}")
    
    def _transform_telemetry_for_coaching(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform telemetry data to coaching agent format"""
        # Map fields from telemetry service to coaching agent expected format
        transformed = {}
        # Updated field mappings to match actual telemetry data
        field_map = {
            'speed': 'speed',
            'brake': 'brake_pct',
            'throttle': 'throttle_pct',
            'steering': 'steering_angle',
            'lapDistPct': 'lap_distance_pct',
            'gear': 'gear',
            'rpm': 'rpm',
            'lapCurrentLapTime': 'current_lap_time',
            'lapLastLapTime': 'last_lap_time'
        }
        for telemetry_key, coaching_key in field_map.items():
            if telemetry_key in telemetry_data:
                transformed[coaching_key] = telemetry_data[telemetry_key]
        # Add session context
        transformed['track_name'] = self.session_state.track_name
        transformed['car_name'] = self.session_state.car_name
        transformed['session_type'] = 'practice'  # Default, could be enhanced
        # Add timestamp
        transformed['timestamp'] = time.time()
        # Check for lap completion
        if 'lapCompleted' in telemetry_data and telemetry_data['lapCompleted']:
            transformed['lap_completed'] = True
        return transformed
    
    def _map_priority_to_number(self, priority):
        """Map message priority to a numeric value for UI"""
        # If priority is an enum, map to int, else fallback to 1
        try:
            return int(priority.value) if hasattr(priority, 'value') else int(priority)
        except Exception:
            return 1

    # =============================================================================
    # TELEMETRY SERVICE CONNECTION
    # =============================================================================
    
    async def connect_to_telemetry_stream(self):
        logger.info(f"Attempting to connect to telemetry stream at ws://{self.telemetry_host}:{self.telemetry_port}")
        while True:
            try:
                async with websockets.connect(f"ws://{self.telemetry_host}:{self.telemetry_port}") as websocket:
                    self.telemetry_websocket = websocket
                    self.telemetry_connected = True
                    logger.info(f"Connected to telemetry stream at ws://{self.telemetry_host}:{self.telemetry_port}")
                    async for message in websocket:
                        await self.handle_telemetry_message(json.loads(message))
            except Exception as e:
                self.telemetry_connected = False
                logger.error(f"Error in telemetry stream connection: {e}")
                await asyncio.sleep(5)
    
    async def connect_to_session_stream(self):
        """Connect to telemetry service's session stream"""
        while True:
            try:
                uri = f"ws://{self.telemetry_host}:{self.session_port}"
                async with websockets.connect(uri) as websocket:
                    logger.info(f"Connected to session stream at {uri}")
                    self.session_websocket = websocket
                    self.session_connected = True
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self.handle_session_message(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from session stream: {message}")
                        except Exception as e:
                            logger.error(f"Error processing session message: {e}")
                            
            except Exception as e:
                self.session_connected = False
                logger.warning(f"Session stream connection failed: {e}")
                await asyncio.sleep(5)  # Retry in 5 seconds
    
    # =============================================================================
    # MESSAGE HANDLERS
    # =============================================================================
    
    async def handle_telemetry_message(self, data: Dict[str, Any]):
        """Process incoming telemetry data"""
        try:
            message_type = data.get("type")
            
            if message_type == "connected":
                logger.info("Telemetry stream connection confirmed")
                return
            
            if message_type == "telemetry":
                telemetry_data = data.get("data", {})
                logger.info(f"handle_telemetry_message: telemetry_data = {telemetry_data}")
                self.latest_telemetry = telemetry_data
                
                # Debug logging
                logger.debug(f"Processing telemetry: Speed={telemetry_data.get('speed', 'N/A')}, UI clients={len(self.ui_clients)}")
                
                # Process telemetry for coaching insights
                processed_data = await self.process_telemetry(telemetry_data)
                
                # Forward to UI clients
                await self.broadcast_to_ui({
                    "type": "telemetry",
                    "data": processed_data,
                    "timestamp": time.time()
                })
                
                # Debug: confirm forwarding
                logger.debug(f"Forwarded telemetry to {len(self.ui_clients)} UI clients")
                
        except Exception as e:
            logger.error(f"Error handling telemetry message: {e}")
    
    async def handle_session_message(self, data: Dict[str, Any]):
        """Process incoming session data"""
        try:
            message_type = data.get("type")
            
            if message_type == "connected":
                logger.info("Session stream connection confirmed")
                return
            
            if message_type == "session":
                session_data = data.get("data", {})
                self.latest_session_data = session_data
                
                # Update session state
                await self.update_session_state(session_data)
                
                # Forward to UI clients
                await self.broadcast_to_ui({
                    "type": "sessionInfo",
                    "data": session_data,
                    "timestamp": time.time()
                })
                
                # Log session changes
                track_name = session_data.get('trackName', 'Unknown Track')
                car_name = session_data.get('carName', 'Unknown Car')
               
        except Exception as e:
            logger.error(f"Error handling session message: {e}")
    
    # =============================================================================
    # DATA PROCESSING
    # =============================================================================
    
    async def process_telemetry(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw telemetry for coaching insights"""
        try:
            # Start with the original telemetry
            processed = telemetry_data.copy()
            
            # Add coaching-specific calculations
            speed = telemetry_data.get('speed', 0)
            rpm = telemetry_data.get('rpm', 0)
            throttle = telemetry_data.get('throttle', 0)
            brake = telemetry_data.get('brake', 0)
            
            # Calculate driving intensity metrics
            processed['drivingIntensity'] = self.calculate_driving_intensity(speed, throttle, brake)
            processed['engineStress'] = self.calculate_engine_stress(rpm, throttle)
            
            # Add session context
            processed['sessionActive'] = self.session_state.is_active
            processed['sessionTrack'] = self.session_state.track_name
            processed['sessionCar'] = self.session_state.car_name
            
            # Add connection status for frontend
            processed['isConnected'] = self.telemetry_connected and self.session_connected
            
            # Process through coaching agent if available
            if self.coaching_agent and self.coaching_agent_active:
                try:
                    enhanced_processed = await self.process_telemetry_with_coaching(processed)
                    processed = enhanced_processed
                except Exception as e:
                    logger.error(f"Error in coaching agent processing: {e}")
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing telemetry: {e}")
            return telemetry_data
    
    def calculate_driving_intensity(self, speed: float, throttle: float, brake: float) -> float:
        """Calculate driving intensity based on speed and inputs"""
        try:
            # Normalize inputs
            speed_factor = min(speed / 150.0, 1.0)  # Normalize to 150 mph max
            input_factor = max(throttle, brake) / 100.0
            
            # Combine factors
            intensity = (speed_factor * 0.6) + (input_factor * 0.4)
            return round(intensity * 100, 1)  # Return as percentage
            
        except Exception:
            return 0.0
    
    def calculate_engine_stress(self, rpm: float, throttle: float) -> float:
        """Calculate engine stress based on RPM and throttle"""
        try:
            # Normalize RPM (assuming 8000 RPM redline)
            rpm_factor = min(rpm / 8000.0, 1.0)
            throttle_factor = throttle / 100.0
            
            # Engine stress is higher at high RPM + high throttle
            stress = (rpm_factor * throttle_factor) * 100
            return round(stress, 1)
            
        except Exception:
            return 0.0
    
    async def update_session_state(self, session_data: Dict[str, Any]):
        """Update internal session state"""
        try:
            track_name = session_data.get('trackName', 'Unknown Track')
            car_name = session_data.get('carName', 'Unknown Car')
            
            # Check if this is a new session
            session_changed = (
                track_name != self.session_state.track_name or
                car_name != self.session_state.car_name
            )
            
            if session_changed:
                logger.info(f"Session change detected: {self.session_state.track_name} -> {track_name}")
                self.session_state.session_start_time = time.time()
            
            # Update state
            self.session_state.track_name = track_name
            self.session_state.car_name = car_name
            self.session_state.last_update_time = time.time()
            self.session_state.is_active = (
                track_name != "Unknown Track" and 
                car_name != "Unknown Car"
            )
            
        except Exception as e:
            logger.error(f"Error updating session state: {e}")
    
    # =============================================================================
    # UI CLIENT HANDLING
    # =============================================================================
    
    async def handle_ui_client(self, websocket, path=None):
        logger.info(f"UI client attempting to connect from {websocket.remote_address}")
        try:
            self.ui_clients.add(websocket)
            logger.info(f"UI client connected from {websocket.remote_address}")
            # Send initial session info
            await websocket.send(json.dumps({
                "type": "sessionInfo",
                "data": {
                    "track": self.session_state.track_name,
                    "car": self.session_state.car_name,
                    "active": self.session_state.is_active
                }
            }))
            logger.info(f"Sent initial session info to UI client {websocket.remote_address}")
            # Keep connection alive
            async for message in websocket:
                try:
                    logger.info(f"Received message from UI client {websocket.remote_address}: {message}")
                    data = json.loads(message)
                    await self.handle_ui_request(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from UI client {websocket.remote_address}: {message}")
                except Exception as e:
                    logger.error(f"Error handling message from UI client {websocket.remote_address}: {e}")
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"UI client {websocket.remote_address} disconnected: {e}")
        except Exception as e:
            logger.error(f"UI client error: {e}")
        finally:
            self.ui_clients.discard(websocket)
            logger.info(f"UI client {websocket.remote_address} removed from active clients")
    
    async def handle_ui_request(self, websocket, data: Dict[str, Any]):
        """Handle requests from UI clients"""
        try:
            request_type = data.get("type")
            
            if request_type == "getStatus":
                # Send service status including coaching agent
                coaching_stats = {}
                if self.coaching_agent and self.coaching_agent_active:
                    coaching_stats = self.coaching_agent.get_stats()
                
                await websocket.send(json.dumps({
                    "type": "status",
                    "data": {
                        "telemetryConnected": self.telemetry_connected,
                        "sessionConnected": self.session_connected,
                        "sessionActive": self.session_state.is_active,
                        "currentTrack": self.session_state.track_name,
                        "currentCar": self.session_state.car_name,
                        "serviceUptime": time.time() - self.session_state.session_start_time if self.session_state.session_start_time else 0,
                        "coachingAgent": {
                            "available": COACHING_AGENT_AVAILABLE,
                            "active": self.coaching_agent_active,
                            "stats": coaching_stats
                        }
                    }
                }))
            
            elif request_type == "setCoachingMode":
                # Set coaching mode
                mode = data.get("mode", "intermediate")
                if self.coaching_agent and self.coaching_agent_active:
                    try:
                        # Import here to avoid module-level import issues
                        sys.path.insert(0, coaching_agent_path)
                        from hybrid_coach import CoachingMode
                        
                        coaching_mode = CoachingMode(mode)
                        self.coaching_agent.set_coaching_mode(coaching_mode)
                        
                        await websocket.send(json.dumps({
                            "type": "coachingModeSet",
                            "data": {"mode": mode, "success": True}
                        }))
                    except ValueError:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "data": {"message": f"Invalid coaching mode: {mode}"}
                        }))
                    except Exception as e:
                        logger.error(f"Error setting coaching mode: {e}")
                        await websocket.send(json.dumps({
                            "type": "error", 
                            "data": {"message": f"Failed to set coaching mode: {str(e)}"}
                        }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "data": {"message": "Coaching agent not available"}
                    }))
            
            elif request_type == "getCoachingStats":
                # Send coaching statistics
                if self.coaching_agent and self.coaching_agent_active:
                    stats = self.coaching_agent.get_stats()
                    await websocket.send(json.dumps({
                        "type": "coachingStats",
                        "data": stats
                    }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "data": {"message": "Coaching agent not available"}
                    }))
            
        except Exception as e:
            logger.error(f"Error handling UI request: {e}")
    
    async def broadcast_to_ui(self, message: Dict[str, Any]):
        """Broadcast message to all UI clients"""
        if not self.ui_clients:
            return
        
        message_json = json.dumps(message)
        disconnected_clients = set()
        
        for client in self.ui_clients:
            try:
                await client.send(message_json)
            except Exception:
                disconnected_clients.add(client)
        
        self.ui_clients -= disconnected_clients
    
    # =============================================================================
    # STATUS MONITORING
    # =============================================================================
    
    async def status_monitor(self):
        """Monitor service connections and status"""
        last_log_time = 0
        
        while True:
            try:
                current_time = time.time()
                
                # Log status every 30 seconds
                if current_time - last_log_time > 30:
                    telemetry_status = "OK" if self.telemetry_connected else "NO"
                    session_status = "OK" if self.session_connected else "NO"
                    coaching_status = "OK" if (self.coaching_agent and self.coaching_agent_active) else "NO"
                    active_session = "YES" if self.session_state.is_active else "NO"
                    logger.info(f"Service Status - Telemetry: {telemetry_status}, Session: {session_status}, Coaching: {coaching_status}, UI Clients: {len(self.ui_clients)}, Active Session: {active_session}")
                    last_log_time = current_time
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in status monitor: {e}")
                await asyncio.sleep(10)
    
    # =============================================================================
    # SERVER STARTUP
    # =============================================================================
    
    async def start_service(self):
        """Start the coaching data service"""
        logger.info(f"Starting Coaching Data Service")
        logger.info(f"Connecting to telemetry stream at ws://{self.telemetry_host}:{self.telemetry_port}")
        logger.info(f"Connecting to session stream at ws://{self.telemetry_host}:{self.session_port}")
        logger.info(f"UI server on ws://{self.ui_host}:{self.ui_port}")
        
        # Start coaching agent if available
        if COACHING_AGENT_AVAILABLE:
            await self.start_coaching_agent()
        else:
            logger.warning("Coaching agent not available - running without AI coaching")
        
        # Start UI server
        ui_server = websockets.serve(self.handle_ui_client, self.ui_host, self.ui_port)
        
        # Start all tasks
        await asyncio.gather(
            ui_server,
            self.connect_to_telemetry_stream(),
            self.connect_to_session_stream(),
            self.coaching_message_processor(),
            self.status_monitor()
        )
    
    async def coaching_message_processor(self):
        """Background task to continuously check for coaching messages"""
        while True:
            try:
                if self.coaching_agent and self.coaching_agent_active:
                    await self._check_for_coaching_messages()
                await asyncio.sleep(0.2)  # Check every 200ms for responsive coaching
            except Exception as e:
                logger.error(f"Error in coaching message processor: {e}")
                await asyncio.sleep(1)

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create and start service
    service = CoachingDataService()
    try:
        asyncio.run(service.start_service())
    except KeyboardInterrupt:
        logger.info("Coaching data service stopped by user")

if __name__ == "__main__":
    main()
