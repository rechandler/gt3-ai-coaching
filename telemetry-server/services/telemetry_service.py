"""
GT3 AI Coaching - Telemetry Service
===================================

This service handles:
1. Connection to iRacing SDK (iRSDK)
2. Collection of raw telemetry data
3. Collection of session/driver data
4. Streaming data to coaching platform via WebSocket

Two main data streams:
- Telemetry Stream: Real-time car performance data (speed, RPM, lap times, etc.)
- Session Stream: Track information, car information, driver information
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, Set
import websockets
import websockets.exceptions
import irsdk
SDK_TYPE = "irsdk"

logger = logging.getLogger(__name__)

class TelemetryService:
    """
    Dedicated service for collecting and streaming iRacing telemetry data.
    
    Responsibilities:
    - Connect to iRacing SDK
    - Collect real-time telemetry data
    - Collect session/driver information
    - Stream data to coaching platform
    """
    
    def __init__(self, host: str = "localhost", telemetry_port: int = 9001, session_port: int = 9002):
        self.host = host
        self.telemetry_port = telemetry_port
        self.session_port = session_port
        
        # Client connections for each stream
        self.telemetry_clients: Set = set()
        self.session_clients: Set = set()
        
        # Connection state
        self.is_connected_to_iracing = False
        
        # Data caching
        self.last_telemetry = {}
        self.last_session_data = {}
        
        # Initialize iRacing SDK
        self.ir = irsdk.IRSDK()
        logger.info(f"Using {SDK_TYPE} for iRacing SDK")
        
        # Start the SDK
        try:
            if hasattr(self.ir, 'startup'):
                startup_result = self.ir.startup()
                logger.info(f"SDK startup result: {startup_result}")
        except Exception as e:
            logger.warning(f"SDK startup failed: {e}")
        
        # Check available methods
        self.available_methods = self._check_available_methods()
    
    def _check_available_methods(self) -> Dict[str, Dict[str, Any]]:
        """Check what methods and attributes are available in this SDK version"""
        methods_to_check = [
            'startup', 'shutdown', 'is_initialized', 'is_connected',
            'session_info', 'get_session_info', 'session_info_update'
        ]
        
        available = {}
        for method in methods_to_check:
            if hasattr(self.ir, method):
                attr = getattr(self.ir, method)
                available[method] = {
                    'exists': True,
                    'callable': callable(attr),
                    'type': type(attr).__name__
                }
            else:
                available[method] = {'exists': False}
        
        logger.info(f"Available SDK methods: {list(k for k, v in available.items() if v.get('exists'))}")
        return available
    
    def safe_get_telemetry(self, key: str) -> Any:
        """Safely get telemetry value from iRSDK"""
        try:
            value = self.ir[key]
            return value
        except (KeyError, TypeError, AttributeError, IndexError):
            return None
        except Exception as e:
            logger.debug(f"Error getting {key}: {e}")
            return None
    
    def check_connection_status(self) -> bool:
        """Check if still connected to iRacing"""
        try:
            # First, ensure SDK is started
            if hasattr(self.ir, 'startup') and hasattr(self.ir, 'is_initialized'):
                try:
                    attr = self.ir.is_initialized
                    initialized = attr() if callable(attr) else attr
                    
                    if not initialized:
                        logger.debug("SDK not initialized, attempting startup...")
                        startup_result = self.ir.startup()
                        if not startup_result:
                            return False
                except Exception as e:
                    logger.debug(f"Error checking initialization: {e}")
                    return False
            
            # Check connection status
            if hasattr(self.ir, 'is_connected') and hasattr(self.ir, 'is_initialized'):
                try:
                    attr = self.ir.is_connected
                    connected = attr() if callable(attr) else attr
                    
                    attr = self.ir.is_initialized
                    initialized = attr() if callable(attr) else attr
                    
                    return bool(connected) and bool(initialized)
                except Exception as e:
                    logger.debug(f"Error calling connection methods: {e}")
            
            # Fallback: Test by getting data
            test_data = self.safe_get_telemetry('SessionTime')
            return test_data is not None
            
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False
    
    # =============================================================================
    # TELEMETRY DATA COLLECTION
    # =============================================================================
    
    def get_telemetry_data(self) -> Optional[Dict[str, Any]]:
        """Get real-time telemetry data only"""
        try:
            telemetry = {}
            
            # Core telemetry fields for GT3 coaching
            telemetry_fields = {
                # Session timing
                'sessionTime': 'SessionTime',
                'sessionTick': 'SessionTick', 
                'sessionFlags': 'SessionFlags',
                'sessionState': 'SessionState',
                'paceFlags': 'PaceFlags',
                
                # Car performance
                'speed': 'Speed',
                'rpm': 'RPM', 
                'gear': 'Gear',
                'throttle': 'Throttle',
                'brake': 'Brake',
                'steering': 'SteeringWheelAngle',
                
                # Lap timing
                'lapCurrentLapTime': 'LapCurrentLapTime',
                'lapLastLapTime': 'LapLastLapTime',
                'lapBestLapTime': 'LapBestLapTime',
                'lapDistPct': 'LapDistPct',
                'lap': 'Lap',
                
                # Delta timing
                'lapDeltaToBestLap': 'LapDeltaToBestLap',
                'lapDeltaToOptimalLap': 'LapDeltaToOptimalLap',
                'lapDeltaToSessionBestLap': 'LapDeltaToSessionBestLap',
                
                # Position and race data
                'position': 'Position',
                'classPosition': 'ClassPosition',
                'playerTrackSurface': 'PlayerTrackSurface',
                
                # Vehicle dynamics
                'yawRate': 'YawRate',
                'yaw': 'Yaw',
                'roll': 'Roll',
                'rollRate': 'RollRate',
                'pitch': 'Pitch',
                'pitchRate': 'PitchRate',
                'velocityX': 'VelocityX',
                'velocityY': 'VelocityY',
                'velocityZ': 'VelocityZ',
                'latAccel': 'LatAccel',
                'longAccel': 'LongAccel',
                'vertAccel': 'VertAccel',
                'steeringTorque': 'SteeringWheelTorque',
                
                # Environmental
                'trackTempCrew': 'TrackTempCrew',
                'airTemp': 'AirTemp',
                'weatherType': 'WeatherType',
                
                # Fuel and pit
                'fuelLevel': 'FuelLevel',
                'fuelLevelPct': 'FuelLevelPct',
                'fuelUsePerHour': 'FuelUsePerHour',
                'onPitRoad': 'OnPitRoad',
                
                # Tire pressures
                'tirePressureLF': 'LFTirePres',
                'tirePressureRF': 'RFTirePres',
                'tirePressureLR': 'LRTirePres', 
                'tirePressureRR': 'RRTirePres'
            }
            
            # Get basic telemetry
            for field_name, irsdk_key in telemetry_fields.items():
                value = self.safe_get_telemetry(irsdk_key)
                if value is not None:
                    # Convert units where needed
                    if field_name == 'speed':
                        value = value * 2.23694  # Convert m/s to MPH
                    elif field_name in ['throttle', 'brake']:
                        value = value * 100  # Convert to percentage
                    elif field_name in ['fuelLevel', 'fuelUsePerHour']:
                        value = value * 0.264172  # Convert liters to US gallons
                    
                    telemetry[field_name] = value
            
            # Calculate delta time
            on_pit_road = self.safe_get_telemetry('OnPitRoad')
            
            # Try native delta fields first
            native_delta = None
            delta_fields = ['LapDeltaToBestLap', 'LapDeltaToOptimalLap', 'LapDeltaToSessionBestLap']
            for delta_field in delta_fields:
                delta_value = self.safe_get_telemetry(delta_field)
                if delta_value is not None and abs(delta_value) < 999:
                    native_delta = delta_value
                    break
            
            # Set delta time
            if not on_pit_road and native_delta is not None:
                telemetry['deltaTime'] = native_delta
                telemetry['deltaSource'] = 'iRacing_native'
            elif not on_pit_road:
                # Fallback calculation
                current_lap_time = self.safe_get_telemetry('LapCurrentLapTime')
                best_lap_time = self.safe_get_telemetry('LapBestLapTime')
                
                if (current_lap_time is not None and best_lap_time is not None and best_lap_time > 0):
                    telemetry['deltaTime'] = current_lap_time - best_lap_time
                    telemetry['deltaSource'] = 'calculated_fallback'
                else:
                    telemetry['deltaTime'] = None
                    telemetry['deltaSource'] = 'unavailable'
            else:
                # In pits - don't show delta
                telemetry['deltaTime'] = None
                telemetry['deltaSource'] = 'in_pits'
            
            # Add timestamp
            telemetry['timestamp'] = time.time()
            telemetry['isConnected'] = True
            
            return telemetry if telemetry else None
                
        except Exception as e:
            logger.error(f"Error getting telemetry data: {e}")
            return None
    
    # =============================================================================
    # SESSION & DRIVER DATA COLLECTION
    # =============================================================================
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get session information from iRSDK"""
        try:
            # Method 1: Direct access to WeekendInfo
            try:
                weekend_info_direct = self.ir['WeekendInfo']
                if weekend_info_direct and isinstance(weekend_info_direct, dict):
                    track_name = weekend_info_direct.get('TrackDisplayName', '')
                    if track_name and track_name not in ['iRacing Track', '']:
                        logger.debug(f"Direct access - Found real track: {track_name}")
                        
                        # Build complete session info structure
                        session_info_raw = {
                            'WeekendInfo': weekend_info_direct,
                            'DriverInfo': {
                                'DriverCarIdx': 0,
                                'Drivers': []
                            },
                            'SessionInfo': {
                                'Sessions': [{
                                    'SessionName': weekend_info_direct.get('EventType', 'Practice'),
                                    'SessionType': weekend_info_direct.get('EventType', 'Practice')
                                }]
                            }
                        }
                        
                        return session_info_raw
            except Exception as e:
                logger.debug(f"Direct WeekendInfo access failed: {e}")
            
            # Method 2: Try other session info methods
            session_info_raw = None
            
            if hasattr(self.ir, 'session_info_update'):
                try:
                    update_available = self.ir.session_info_update
                    session_info_raw = getattr(self.ir, 'session_info', None)
                except Exception as e:
                    logger.debug(f"Method 2 failed: {e}")
            
            if not session_info_raw and self.available_methods.get('session_info', {}).get('exists'):
                try:
                    session_info_raw = getattr(self.ir, 'session_info', None)
                except Exception as e:
                    logger.debug(f"Method 3 failed: {e}")
            
            # Parse YAML/JSON if needed
            if session_info_raw and isinstance(session_info_raw, str):
                try:
                    import yaml
                    session_info_raw = yaml.safe_load(session_info_raw)
                except ImportError:
                    try:
                        session_info_raw = json.loads(session_info_raw)
                    except:
                        session_info_raw = None
            
            return session_info_raw
            
        except Exception as e:
            logger.warning(f"Session info unavailable: {e}")
            return None
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get track/session information"""
        try:
            track_name = ""
            track_config = ""
            category = ""
            # Try to get from session info first
            session_info = self.get_session_info()
            if session_info:
                weekend_info = session_info.get('WeekendInfo', {})
                track_name = weekend_info.get('TrackDisplayName', '')
                track_config = weekend_info.get('TrackConfigName', '')
                category = weekend_info.get('Category', '')

            # Build full track name
            full_track_name = f"{track_name} - {track_config}"

            return {
                'trackName': track_name,
                'trackConfig': track_config,
                'fullTrackName': full_track_name,
                'category': category,
                'timestamp': time.time(),
                'session_active': bool(session_info)
            }
            
        except Exception as e:
            logger.error(f"Error getting session data: {e}")
            return {
                'trackName': "Unknown Track",
                'trackConfig': "",
                'fullTrackName': "Unknown Track",
                'category': "",
                'timestamp': time.time(),
            }
    
    def get_driver_data(self) -> Dict[str, Any]:
        """Get driver/car information"""
        try:
            car_name = "Unknown Car"
            
            # Try to get car name from DriverInfo
            try:
                driver_info = self.ir['DriverInfo']
                if isinstance(driver_info, dict) and 'Drivers' in driver_info and len(driver_info['Drivers']) > 0:
                    player_car_idx = driver_info.get('DriverCarIdx', 0)
                    
                    # Find the player's driver entry
                    player_driver = None
                    for driver in driver_info['Drivers']:
                        if driver.get('CarIdx') == player_car_idx:
                            player_driver = driver
                            break
                    
                    if player_driver:
                        driver_car_name = player_driver.get('CarScreenName', '')
                        if driver_car_name and driver_car_name not in ['GT3 Car', 'Race Car']:
                            car_name = driver_car_name
                    else:
                        # Fallback to first driver
                        if len(driver_info['Drivers']) > 0:
                            driver_car_name = driver_info['Drivers'][0].get('CarScreenName', '')
                            if driver_car_name and driver_car_name not in ['GT3 Car', 'Race Car']:
                                car_name = driver_car_name
            except Exception as e:
                logger.debug(f"Could not get car from DriverInfo: {e}")
            
            # Final fallback to telemetry
            if car_name == "Unknown Car":
                car_screen_name = self.safe_get_telemetry('CarScreenName')
                if car_screen_name and car_screen_name not in ['GT3 Car', 'Race Car', '']:
                    car_name = car_screen_name
                else:
                    car_screen_name_short = self.safe_get_telemetry('CarScreenNameShort')
                    if car_screen_name_short and car_screen_name_short not in ['GT3 Car', 'Race Car', '']:
                        car_name = car_screen_name_short
            
            return {
                'carName': car_name,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting driver data: {e}")
            return {
                'carName': "Unknown Car",
                'timestamp': time.time()
            }
    
    # =============================================================================
    # WEBSOCKET HANDLERS
    # =============================================================================
    
    async def handle_telemetry_client(self, websocket, path=None):
        """Handle telemetry stream clients"""
        try:
            logger.info(f"Telemetry client connected from {websocket.remote_address}")
            self.telemetry_clients.add(websocket)
            
            # Send initial connection message
            await websocket.send(json.dumps({
                "type": "connected",
                "stream": "telemetry",
                "message": "Connected to telemetry stream"
            }))
            
            # Send current telemetry if available
            if self.last_telemetry:
                await websocket.send(json.dumps({
                    "type": "telemetry",
                    "data": self.last_telemetry
                }))
            
            # Keep connection alive
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Handle client requests if needed
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from telemetry client: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.debug("Telemetry client disconnected")
        except Exception as e:
            logger.debug(f"Telemetry client error: {e}")
        finally:
            self.telemetry_clients.discard(websocket)
    
    async def handle_session_client(self, websocket, path=None):
        """Handle session stream clients"""
        try:
            logger.info(f"Session client connected from {websocket.remote_address}")
            self.session_clients.add(websocket)
            
            # Send initial connection message
            await websocket.send(json.dumps({
                "type": "connected",
                "stream": "session",
                "message": "Connected to session stream"
            }))
            
            # Send current session data if available
            if self.last_session_data:
                await websocket.send(json.dumps({
                    "type": "session",
                    "data": self.last_session_data
                }))
            
            # Keep connection alive
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Handle client requests if needed
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from session client: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.debug("Session client disconnected")
        except Exception as e:
            logger.debug(f"Session client error: {e}")
        finally:
            self.session_clients.discard(websocket)
    
    async def broadcast_telemetry(self, data: Dict[str, Any]):
        """Broadcast telemetry data to all connected clients"""
        if not self.telemetry_clients:
            return
        
        message = json.dumps({
            "type": "telemetry",
            "data": data
        })
        
        disconnected_clients = set()
        for client in self.telemetry_clients:
            try:
                await client.send(message)
            except Exception:
                disconnected_clients.add(client)
        
        self.telemetry_clients -= disconnected_clients
    
    async def broadcast_session(self, data: Dict[str, Any]):
        """Broadcast session data to all connected clients"""
        if not self.session_clients:
            return
        
        message = json.dumps({
            "type": "session",
            "data": data
        })
        
        disconnected_clients = set()
        for client in self.session_clients:
            try:
                await client.send(message)
            except Exception:
                disconnected_clients.add(client)
        
        self.session_clients -= disconnected_clients
    
    # =============================================================================
    # MAIN LOOPS
    # =============================================================================
    
    async def telemetry_loop(self):
        """Main telemetry collection and broadcasting loop"""
        last_telemetry_time = 0
        
        while True:
            try:
                # Check connection
                if not self.check_connection_status():
                    if self.is_connected_to_iracing:
                        logger.info("❌ Lost connection to iRacing")
                        self.is_connected_to_iracing = False
                    await asyncio.sleep(2)
                    continue
                
                if not self.is_connected_to_iracing:
                    logger.info("✅ Connected to iRacing!")
                    self.is_connected_to_iracing = True
                
                # Get telemetry data
                telemetry = self.get_telemetry_data()
                if telemetry:
                    self.last_telemetry = telemetry
                    await self.broadcast_telemetry(telemetry)
                    
                    # Log occasionally
                    current_time = time.time()
                    if current_time - last_telemetry_time > 10:
                        logger.info(f"📊 Telemetry streaming (Speed: {telemetry.get('speed', 0):.1f} mph, RPM: {telemetry.get('rpm', 0):.0f})")
                        last_telemetry_time = current_time
                
                # Update at 60Hz
                await asyncio.sleep(1/60)
                
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                await asyncio.sleep(1)
    
    async def session_loop(self):
        """Session/driver data collection and broadcasting loop"""
        last_session_time = 0
        session_update_interval = 5.0  # Update every 5 seconds
        
        while True:
            try:
                if not self.is_connected_to_iracing:
                    await asyncio.sleep(2)
                    continue
                
                current_time = time.time()
                if current_time - last_session_time >= session_update_interval:
                    # Get session and driver data
                    session_data = self.get_session_data()
                    driver_data = self.get_driver_data()
                    
                    combined_session_data = {
                        **session_data,
                        **driver_data
                    }
                    
                    # Check if data has changed
                    if combined_session_data != self.last_session_data:
                        self.last_session_data = combined_session_data
                        await self.broadcast_session(combined_session_data)
                        
                        logger.info(f"🏁 Session info: Track='{session_data['fullTrackName']}', Car='{driver_data['carName']}'")
                    
                    last_session_time = current_time
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in session loop: {e}")
                await asyncio.sleep(1)
    
    # =============================================================================
    # SERVER STARTUP
    # =============================================================================
    
    async def start_servers(self):
        """Start both WebSocket servers"""
        logger.info(f"🚀 Starting Telemetry Service")
        logger.info(f"📊 Telemetry stream on ws://{self.host}:{self.telemetry_port}")
        logger.info(f"🏁 Session stream on ws://{self.host}:{self.session_port}")
        
        # Start both servers
        telemetry_server = websockets.serve(self.handle_telemetry_client, self.host, self.telemetry_port)
        session_server = websockets.serve(self.handle_session_client, self.host, self.session_port)
        
        await asyncio.gather(
            telemetry_server,
            session_server,
            self.telemetry_loop(),
            self.session_loop()
        )

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create and start service
    service = TelemetryService()
    try:
        asyncio.run(service.start_servers())
    except KeyboardInterrupt:
        logger.info("🏁 Telemetry service stopped by user")

if __name__ == "__main__":
    main()
