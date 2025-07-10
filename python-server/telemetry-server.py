#!/usr/bin/env python3
"""
GT3 AI Coaching - Python iRacing Telemetry Server
Robust version that works with any pyirsdk variant
"""

import asyncio
import json
import logging
import websockets
from websockets.server import serve
import time
from typing import Dict, Any, Optional

# Try different iRacing SDK imports
try:
    import pyirsdk as irsdk
    SDK_TYPE = "pyirsdk"
    print("Using pyirsdk")
except ImportError:
    try:
        import irsdk
        SDK_TYPE = "irsdk"
        print("Using irsdk")
    except ImportError:
        print("ERROR: No iRacing SDK found. Please install:")
        print("  pip install git+https://github.com/kutu/pyirsdk.git")
        exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GT3TelemetryServer:
    def __init__(self, host: str = "localhost", port: int = 8081):
        self.host = host
        self.port = port
        self.connected_clients = set()
        self.is_connected_to_iracing = False
        self.last_telemetry = {}
        self.last_session_info = {}
        
        # Initialize iRacing SDK
        self.ir = irsdk.IRSDK()
        logger.info(f"Using {SDK_TYPE} for iRacing SDK")
        
        # Track what methods/attributes are available
        self.available_methods = {}
        self.check_available_methods()
        
    def check_available_methods(self):
        """Check what methods and attributes are available in this SDK version"""
        methods_to_check = [
            'startup', 'shutdown', 'is_initialized', 'is_connected',
            'session_info', 'get_session_info', 'session_info_update'
        ]
        
        for method in methods_to_check:
            if hasattr(self.ir, method):
                attr = getattr(self.ir, method)
                self.available_methods[method] = {
                    'exists': True,
                    'callable': callable(attr),
                    'type': type(attr).__name__
                }
            else:
                self.available_methods[method] = {'exists': False}
        
        logger.info(f"Available SDK methods: {list(k for k, v in self.available_methods.items() if v.get('exists'))}")
        
    async def handle_client(self, websocket, path):
        """Handle new WebSocket client connections"""
        logger.info(f"GT3 AI Coaching client connected from {websocket.remote_address}")
        self.connected_clients.add(websocket)
        
        try:
            # Send initial connection message
            await websocket.send(json.dumps({
                "type": "Connected",
                "message": "Connected to GT3 Python Telemetry Server"
            }))
            
            # Keep the connection alive
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("GT3 AI Coaching client disconnected")
        finally:
            self.connected_clients.discard(websocket)
    
    async def handle_client_message(self, websocket, message: Dict[str, Any]):
        """Handle messages from GT3 AI coaching app"""
        msg_type = message.get("type")
        
        if msg_type == "request_session_info":
            if self.last_session_info:
                await websocket.send(json.dumps({
                    "type": "SessionInfo",
                    "data": self.last_session_info
                }))
        elif msg_type == "request_telemetry":
            if self.last_telemetry:
                await websocket.send(json.dumps({
                    "type": "Telemetry",
                    "data": self.last_telemetry
                }))
    
    async def broadcast_to_clients(self, message: Dict[str, Any]):
        """Broadcast message to all connected GT3 clients"""
        if not self.connected_clients:
            return
            
        message_json = json.dumps(message)
        disconnected_clients = set()
        
        for client in self.connected_clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected_clients
    
    def connect_to_iracing(self) -> bool:
        """Attempt to connect to iRacing"""
        try:
            # Try startup if available
            if self.available_methods.get('startup', {}).get('callable'):
                success = self.ir.startup()
                if not success:
                    return False
            
            # Check connection - try different methods
            if self.available_methods.get('is_connected', {}).get('exists'):
                connected = getattr(self.ir, 'is_connected', False)
                if self.available_methods.get('is_initialized', {}).get('exists'):
                    initialized = getattr(self.ir, 'is_initialized', False)
                    return connected and initialized
                return connected
            else:
                # Test connection by trying to get some data
                try:
                    test_data = self.ir['SessionTime']
                    return test_data is not None
                except:
                    return False
                    
        except Exception as e:
            logger.debug(f"Connection attempt failed: {e}")
            return False
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get session information - simplified version"""
        try:
            # Skip session info for now if it's causing issues
            # Focus on telemetry data which is more important for GT3 coaching
            logger.debug("Skipping session info to avoid API compatibility issues")
            
            # Create minimal session info
            basic_session_info = {
                'WeekendInfo': {
                    'TrackDisplayName': 'iRacing Track',
                    'TrackConfigName': '',
                    'TrackID': 0,
                    'TrackLength': '0.00 km'
                },
                'DriverInfo': {
                    'DriverCarIdx': 0,
                    'Drivers': [{
                        'CarIdx': 0,
                        'CarScreenName': 'GT3 Car',
                        'CarPath': 'gt3',
                        'CarID': 0
                    }]
                },
                'SessionInfo': {
                    'Sessions': [{
                        'SessionName': 'Practice',
                        'SessionType': 'Practice'
                    }]
                }
            }
            
            return basic_session_info
            
        except Exception as e:
            logger.warning(f"Session info unavailable: {e}")
            return None
    
    def safe_get_telemetry(self, key: str):
        """Safely get telemetry value"""
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
            # Method 1: Check status attributes
            if self.available_methods.get('is_connected', {}).get('exists'):
                connected = getattr(self.ir, 'is_connected', False)
                if self.available_methods.get('is_initialized', {}).get('exists'):
                    initialized = getattr(self.ir, 'is_initialized', False)
                    return bool(connected and initialized)
                return bool(connected)
            
            # Method 2: Test by getting data
            test_data = self.safe_get_telemetry('SessionTime')
            return test_data is not None
            
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False
    
    def get_telemetry_data(self) -> Optional[Dict[str, Any]]:
        """Get telemetry data - focus on core GT3 coaching data"""
        try:
            telemetry = {}
            data_count = 0
            
            # Core telemetry fields for GT3 coaching
            telemetry_fields = {
                # Session data
                'SessionTime': 'SessionTime',
                'SessionTick': 'SessionTick', 
                'SessionFlags': 'SessionFlags',
                'PaceFlags': 'PaceFlags',
                
                # Car performance
                'Speed': 'Speed',
                'RPM': 'RPM', 
                'Gear': 'Gear',
                'Throttle': 'Throttle',
                'Brake': 'Brake',
                'Steering': 'Steering',
                
                # Lap timing
                'LapCurrentLapTime': 'LapCurrentLapTime',
                'LapLastLapTime': 'LapLastLapTime',
                'LapBestLapTime': 'LapBestLapTime',
                'LapDistPct': 'LapDistPct',
                
                # Environmental
                'TrackTempCrew': 'TrackTempCrew',
                'AirTemp': 'AirTemp',
                'WeatherType': 'WeatherType',
                
                # Fuel
                'FuelLevel': 'FuelLevel',
                'FuelLevelPct': 'FuelLevelPct',
                'FuelUsePerHour': 'FuelUsePerHour',
            }
            
            # Get basic telemetry
            for field_name, irsdk_key in telemetry_fields.items():
                value = self.safe_get_telemetry(irsdk_key)
                if value is not None:
                    telemetry[field_name] = value
                    data_count += 1
            
            # Get tire temperatures (GT3 critical)
            tire_temps = {}
            for corner in ['LF', 'RF', 'LR', 'RR']:
                for zone in ['TempCL', 'TempCM', 'TempCR']:
                    key = f'{corner}{zone}'
                    temp = self.safe_get_telemetry(key)
                    if temp is not None:
                        tire_temps[key] = temp
                        data_count += 1
            
            if tire_temps:
                telemetry['TireTemps'] = tire_temps
            
            # Get tire pressures
            tire_pressures = {}
            for corner in ['LF', 'RF', 'LR', 'RR']:
                key = f'{corner}TirePres'
                pressure = self.safe_get_telemetry(key)
                if pressure is not None:
                    tire_pressures[key] = pressure
                    data_count += 1
            
            if tire_pressures:
                telemetry['TirePressures'] = tire_pressures
            
            # Get brake pressures
            brake_pressures = {}
            for corner in ['LF', 'RF', 'LR', 'RR']:
                key = f'{corner}brakeLinePress'
                pressure = self.safe_get_telemetry(key)
                if pressure is not None:
                    brake_pressures[key] = pressure
                    data_count += 1
            
            if brake_pressures:
                telemetry['BrakePressures'] = brake_pressures
            
            # Only return if we got some real data
            if data_count > 5:  # Need at least some basic telemetry
                return telemetry
            else:
                return None
            
        except Exception as e:
            logger.error(f"Error getting telemetry: {e}")
            return None
    
    async def telemetry_loop(self):
        """Main telemetry collection loop"""
        logger.info("Starting GT3 telemetry collection...")
        connection_retry_count = 0
        last_telemetry_time = 0
        
        while True:
            try:
                # Check if we're connected to iRacing
                if not self.is_connected_to_iracing:
                    if self.connect_to_iracing():
                        self.is_connected_to_iracing = True
                        connection_retry_count = 0
                        logger.info("✅ Connected to iRacing!")
                        
                        await self.broadcast_to_clients({
                            "type": "Connected",
                            "message": "iRacing connected"
                        })
                        
                        # Send basic session info
                        session_info = self.get_session_info()
                        if session_info:
                            self.last_session_info = session_info
                            await self.broadcast_to_clients({
                                "type": "SessionInfo", 
                                "data": session_info
                            })
                            logger.info("📋 Basic session info sent to clients")
                    else:
                        connection_retry_count += 1
                        if connection_retry_count % 12 == 0:  # Log every minute
                            logger.info(f"⏳ Waiting for iRacing... (attempt {connection_retry_count})")
                        await asyncio.sleep(5)
                        continue
                
                # Check if still connected
                if not self.check_connection_status():
                    logger.info("❌ Lost connection to iRacing")
                    self.is_connected_to_iracing = False
                    await self.broadcast_to_clients({
                        "type": "Disconnected",
                        "message": "iRacing disconnected"
                    })
                    continue
                
                # Get telemetry data
                telemetry = self.get_telemetry_data()
                if telemetry:
                    self.last_telemetry = telemetry
                    
                    # Log PaceFlags when they change (no converter errors!)
                    if 'PaceFlags' in telemetry and telemetry['PaceFlags'] != 0:
                        logger.debug(f"🏁 PaceFlags: {telemetry['PaceFlags']}")
                    
                    await self.broadcast_to_clients({
                        "type": "Telemetry",
                        "data": telemetry
                    })
                    
                    # Log successful telemetry occasionally
                    current_time = time.time()
                    if current_time - last_telemetry_time > 10:  # Every 10 seconds
                        logger.info(f"📊 Telemetry streaming (Speed: {telemetry.get('Speed', 0):.1f} mph, RPM: {telemetry.get('RPM', 0):.0f})")
                        last_telemetry_time = current_time
                
                # Update at 60Hz for responsive GT3 coaching
                await asyncio.sleep(1/60)
                
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                await asyncio.sleep(1)
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"🚀 Starting GT3 telemetry server on {self.host}:{self.port}")
        
        async with serve(self.handle_client, self.host, self.port):
            logger.info(f"✅ GT3 telemetry server running on ws://{self.host}:{self.port}")
            logger.info("🎯 Waiting for iRacing and GT3 AI Coaching to connect...")
            logger.info("💡 Start iRacing and go to any session to begin telemetry streaming")
            
            # Start the telemetry collection loop
            await self.telemetry_loop()

def main():
    server = GT3TelemetryServer()
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("🏁 GT3 telemetry server stopped by user")

if __name__ == "__main__":
    main()