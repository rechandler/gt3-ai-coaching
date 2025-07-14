"""
Coaching Data Service
====================

This service handles:
1. Receiving telemetry and session data from the telemetry service
2. Processing telemetry for coaching insights
3. Maintaining session persistence 
4. Forwarding processed data to the coaching UI

This service acts as the bridge between raw telemetry and the AI coaching platform.
"""

import asyncio
import json
import logging
import time
import websockets
import websockets.exceptions
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
    
    # =============================================================================
    # TELEMETRY SERVICE CONNECTION
    # =============================================================================
    
    async def connect_to_telemetry_stream(self):
        """Connect to telemetry service's telemetry stream"""
        while True:
            try:
                uri = f"ws://{self.telemetry_host}:{self.telemetry_port}"
                async with websockets.connect(uri) as websocket:
                    logger.info(f"📊 Connected to telemetry stream at {uri}")
                    self.telemetry_websocket = websocket
                    self.telemetry_connected = True
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self.handle_telemetry_message(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from telemetry stream: {message}")
                        except Exception as e:
                            logger.error(f"Error processing telemetry message: {e}")
                            
            except Exception as e:
                self.telemetry_connected = False
                logger.warning(f"Telemetry stream connection failed: {e}")
                await asyncio.sleep(5)  # Retry in 5 seconds
    
    async def connect_to_session_stream(self):
        """Connect to telemetry service's session stream"""
        while True:
            try:
                uri = f"ws://{self.telemetry_host}:{self.session_port}"
                async with websockets.connect(uri) as websocket:
                    logger.info(f"🏁 Connected to session stream at {uri}")
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
                logger.info("📊 Telemetry stream connection confirmed")
                return
            
            if message_type == "telemetry":
                telemetry_data = data.get("data", {})
                self.latest_telemetry = telemetry_data
                
                # Process telemetry for coaching insights
                processed_data = await self.process_telemetry(telemetry_data)
                
                # Forward to UI clients
                await self.broadcast_to_ui({
                    "type": "telemetry",
                    "data": processed_data,
                    "timestamp": time.time()
                })
                
        except Exception as e:
            logger.error(f"Error handling telemetry message: {e}")
    
    async def handle_session_message(self, data: Dict[str, Any]):
        """Process incoming session data"""
        try:
            message_type = data.get("type")
            
            if message_type == "connected":
                logger.info("🏁 Session stream connection confirmed")
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
                logger.info(f"🏁 Session update: Track='{track_name}', Car='{car_name}'")
                
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
                logger.info(f"🔄 Session change detected: {self.session_state.track_name} → {track_name}")
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
        """Handle coaching UI client connections"""
        try:
            logger.info(f"🖥️ UI client connected from {websocket.remote_address}")
            self.ui_clients.add(websocket)
            
            # Send initial connection message
            await websocket.send(json.dumps({
                "type": "connected",
                "message": "Connected to coaching data service",
                "services": {
                    "telemetry": self.telemetry_connected,
                    "session": self.session_connected
                }
            }))
            
            # Send current session data if available
            if self.latest_session_data:
                await websocket.send(json.dumps({
                    "type": "sessionInfo",
                    "data": self.latest_session_data,
                    "timestamp": time.time()
                }))
            
            # Send current telemetry if available
            if self.latest_telemetry:
                processed_telemetry = await self.process_telemetry(self.latest_telemetry)
                await websocket.send(json.dumps({
                    "type": "telemetry",
                    "data": processed_telemetry,
                    "timestamp": time.time()
                }))
            
            # Keep connection alive
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Handle UI client requests if needed
                    await self.handle_ui_request(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from UI client: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.debug("UI client disconnected")
        except Exception as e:
            logger.debug(f"UI client error: {e}")
        finally:
            self.ui_clients.discard(websocket)
    
    async def handle_ui_request(self, websocket, data: Dict[str, Any]):
        """Handle requests from UI clients"""
        try:
            request_type = data.get("type")
            
            if request_type == "getStatus":
                # Send service status
                await websocket.send(json.dumps({
                    "type": "status",
                    "data": {
                        "telemetryConnected": self.telemetry_connected,
                        "sessionConnected": self.session_connected,
                        "sessionActive": self.session_state.is_active,
                        "currentTrack": self.session_state.track_name,
                        "currentCar": self.session_state.car_name,
                        "serviceUptime": time.time() - self.session_state.session_start_time if self.session_state.session_start_time else 0
                    }
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
                    logger.info(f"📈 Service Status - Telemetry: {'✅' if self.telemetry_connected else '❌'}, "
                              f"Session: {'✅' if self.session_connected else '❌'}, "
                              f"UI Clients: {len(self.ui_clients)}, "
                              f"Active Session: {'✅' if self.session_state.is_active else '❌'}")
                    last_log_time = current_time
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in status monitor: {e}")
                await asyncio.sleep(10)
    
    # =============================================================================
    # SERVER STARTUP
    # =============================================================================
    
    async def start_service(self):
        """Start the coaching data service"""
        logger.info(f"🚀 Starting Coaching Data Service")
        logger.info(f"📊 Connecting to telemetry stream at ws://{self.telemetry_host}:{self.telemetry_port}")
        logger.info(f"🏁 Connecting to session stream at ws://{self.telemetry_host}:{self.session_port}")
        logger.info(f"🖥️ UI server on ws://{self.ui_host}:{self.ui_port}")
        
        # Start UI server
        ui_server = websockets.serve(self.handle_ui_client, self.ui_host, self.ui_port)
        
        # Start all tasks
        await asyncio.gather(
            ui_server,
            self.connect_to_telemetry_stream(),
            self.connect_to_session_stream(),
            self.status_monitor()
        )

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
        logger.info("🏁 Coaching data service stopped by user")

if __name__ == "__main__":
    main()
