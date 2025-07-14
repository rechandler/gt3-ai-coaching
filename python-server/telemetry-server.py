#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GT3 AI Coaching - Python iRacing Telemetry Server
Robust version that works with any pyirsdk variant
"""

import asyncio
import json
import logging
import websockets
import time
from typing import Dict, Any, Optional
import sys
import io

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    # Set default encoding for stdout/stderr
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        # Fallback for older Python versions
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import our local AI coach - REMOVED, now handled by coaching-server.py
# from ai_coach import LocalAICoach

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

# Configure logging with rotation to prevent memory issues
import logging.handlers
import os

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Set logging level based on environment
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
if LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
    LOG_LEVEL = 'INFO'

# Configure logger with rotation
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# Create rotating file handler (10MB max, keep 5 files) with UTF-8 encoding
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(logs_dir, 'telemetry-server.log'),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'  # Ensure UTF-8 encoding for log files
)
file_handler.setLevel(getattr(logging, LOG_LEVEL))

# Create console handler for immediate feedback
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Always show INFO+ on console

# Create formatters
detailed_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler.setFormatter(detailed_formatter)
console_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Prevent duplicate logs
logger.propagate = False

class GT3TelemetryServer:
    def __init__(self, host: str = "localhost", port: int = 8081):
        self.host = host
        self.port = port
        self.connected_clients = set()
        self.is_connected_to_iracing = False
        self.last_telemetry = {}
        self.last_session_info = {}
        
        # Cached session info to avoid re-extraction once we have valid values
        self._cached_track_name = None
        self._cached_car_name = None
        self._session_cache_valid = False
        
        # Coaching server connection for sending telemetry data
        self.coaching_server_ws = None
        
        # Initialize iRacing SDK
        self.ir = irsdk.IRSDK()
        logger.info(f"Using {SDK_TYPE} for iRacing SDK")
        
        # Start the SDK immediately
        try:
            if hasattr(self.ir, 'startup'):
                startup_result = self.ir.startup()
                logger.info(f"SDK startup result: {startup_result}")
            else:
                logger.info("No startup method available - SDK may auto-initialize")
        except Exception as e:
            logger.warning(f"SDK startup failed: {e}")
        
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
        
    async def handle_client(self, websocket, path=None):
        """Handle new WebSocket client connections"""
        try:
            logger.info(f"GT3 AI Coaching client connected from {websocket.remote_address}")
            self.connected_clients.add(websocket)
            
            # Send initial connection message
            await websocket.send(json.dumps({
                "type": "Connected",
                "message": "Connected to GT3 Python Telemetry Server",
                "isConnected": self.is_connected_to_iracing
            }))
            
            # Send current session info to newly connected client
            if self.last_session_info:
                await websocket.send(json.dumps({
                    "type": "SessionInfo",
                    "data": self.last_session_info
                }))
                logger.debug(f"📤 Sent current session info to new client")
            
            # Keep the connection alive
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.debug("GT3 AI Coaching client disconnected normally")
        except EOFError:
            logger.debug("Client connection closed unexpectedly (EOFError)")
        except Exception as e:
            logger.debug(f"Client connection error: {e}")
        finally:
            self.connected_clients.discard(websocket)
    
    async def handle_client_message(self, websocket, message: Dict[str, Any]):
        """Handle messages from GT3 AI coaching app"""
        msg_type = message.get("type")
        
        if msg_type == "request_session_info":
            if self.last_session_info:
                # Update session info with real-time car name from DriverInfo before sending
                updated_session_info = self.last_session_info.copy()
                
                # Get real car name from DriverInfo structure (CORRECT METHOD)
                real_car_name = None
                try:
                    driver_info = self.ir['DriverInfo']
                    if driver_info and 'Drivers' in driver_info and len(driver_info['Drivers']) > 0:
                        # Get the player's car index to find the right driver
                        player_car_idx = driver_info.get('DriverCarIdx')
                        logger.info(f"🔍 SESSION REQUEST DEBUG - Player car index: {player_car_idx}")
                        
                        # Find the player's driver entry
                        player_driver = None
                        for driver in driver_info['Drivers']:
                            if driver.get('CarIdx') == player_car_idx:
                                player_driver = driver
                                break
                        
                        if player_driver:
                            real_car_name = player_driver.get('CarScreenName', '')
                            logger.info(f"🔍 SESSION REQUEST DEBUG - Real car name from player's DriverInfo: '{real_car_name}'")
                        else:
                            logger.warning(f"🔍 SESSION REQUEST DEBUG - Could not find player driver with CarIdx {player_car_idx}")
                            # Fallback to first driver
                            if len(driver_info['Drivers']) > 0:
                                real_car_name = driver_info['Drivers'][0].get('CarScreenName', '')
                                logger.warning(f"🔍 SESSION REQUEST DEBUG - Using fallback driver car name: '{real_car_name}'")
                    else:
                        logger.warning(f"🔍 SESSION REQUEST DEBUG - DriverInfo structure missing or empty")
                except Exception as e:
                    logger.warning(f"🔍 SESSION REQUEST DEBUG - Could not access DriverInfo: {e}")
                    # Fallback to telemetry
                    real_car_name = self.safe_get_telemetry('CarScreenName')
                    logger.info(f"🔍 SESSION REQUEST DEBUG - Fallback car name from telemetry: '{real_car_name}'")
                
                if real_car_name and real_car_name not in ['GT3 Car', 'Race Car', '', None]:
                    # Update the DriverInfo with real car name - find the correct player driver
                    if 'DriverInfo' in updated_session_info and 'Drivers' in updated_session_info['DriverInfo']:
                        drivers = updated_session_info['DriverInfo']['Drivers']
                        player_car_idx = updated_session_info['DriverInfo'].get('DriverCarIdx', 0)
                        
                        # Find the player's driver entry to update
                        player_driver_updated = False
                        for driver in drivers:
                            if driver.get('CarIdx') == player_car_idx:
                                old_name = driver.get('CarScreenName', 'Unknown')
                                driver['CarScreenName'] = real_car_name
                                logger.info(f"✅ Updated player driver (CarIdx {player_car_idx}) with real car name: '{old_name}' → '{real_car_name}'")
                                player_driver_updated = True
                                break
                        
                        # Fallback: update first driver if player not found
                        if not player_driver_updated and len(drivers) > 0:
                            old_name = drivers[0].get('CarScreenName', 'Unknown')
                            drivers[0]['CarScreenName'] = real_car_name
                            logger.info(f"✅ Updated fallback driver with real car name: '{old_name}' → '{real_car_name}'")
                else:
                    logger.warning(f"⚠️  No valid real car name available, keeping existing: '{updated_session_info.get('DriverInfo', {}).get('Drivers', [{}])[0].get('CarScreenName', 'Unknown')}'")
                
                # Log what we're about to send
                final_car_name = updated_session_info.get('DriverInfo', {}).get('Drivers', [{}])[0].get('CarScreenName', 'Unknown')
                logger.info(f"🚗 SENDING session info with car name: '{final_car_name}'")
                
                await websocket.send(json.dumps({
                    "type": "SessionInfo",
                    "data": updated_session_info
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
            except (websockets.exceptions.ConnectionClosed, EOFError, Exception) as e:
                logger.debug(f"Removing disconnected client: {e}")
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
                try:
                    # Check if methods are callable or properties
                    if self.available_methods.get('is_connected', {}).get('callable'):
                        connected = self.ir.is_connected()
                    else:
                        connected = self.ir.is_connected
                        
                    if self.available_methods.get('is_initialized', {}).get('exists'):
                        if self.available_methods.get('is_initialized', {}).get('callable'):
                            initialized = self.ir.is_initialized()
                        else:
                            initialized = self.ir.is_initialized
                        return connected and initialized
                    return connected
                except Exception as e:
                    logger.debug(f"Error calling connection methods: {e}")
                    return False
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
        """Get session information - extract real data when possible"""
        try:
            # Method 1: Direct access to WeekendInfo like in raw Python session
            try:
                weekend_info_direct = self.ir['WeekendInfo']
                if weekend_info_direct and isinstance(weekend_info_direct, dict):
                    track_name = weekend_info_direct.get('TrackDisplayName', '')
                    if track_name and track_name not in ['iRacing Track', '']:
                        logger.info(f"🎯 DIRECT ACCESS SUCCESS - Found real track: {track_name}")
                        
                        # Try to get real car info from telemetry
                        real_car_name = self.safe_get_telemetry('CarScreenName')
                        real_car_class = self.safe_get_telemetry('CarClassShortName')
                        
                        # Use real car name if available, otherwise use a better fallback
                        car_name_to_use = real_car_name if real_car_name and real_car_name not in ['GT3 Car', 'Race Car', ''] else None
                        if not car_name_to_use:
                            # Try alternative car name fields
                            car_name_to_use = self.safe_get_telemetry('CarScreenNameShort') or 'GT3 Car'
                        
                        logger.info(f"🚗 Direct access using car name: '{car_name_to_use}' (real: '{real_car_name}')")
                        
                        # Build complete session info from direct access
                        session_info_raw = {
                            'WeekendInfo': weekend_info_direct,
                            'DriverInfo': {
                                'DriverCarIdx': 0,
                                'Drivers': [{
                                    'CarIdx': 0,
                                    'CarScreenName': car_name_to_use,
                                    'CarPath': 'gt3',
                                    'CarID': 0,
                                    'CarClassShortName': real_car_class or 'GT3'
                                }]
                            },
                            'SessionInfo': {
                                'Sessions': [{
                                    'SessionName': weekend_info_direct.get('EventType', 'Practice'),
                                    'SessionType': weekend_info_direct.get('EventType', 'Practice')
                                }]
                            }
                        }
                        
                        logger.info(f"✅ DIRECT ACCESS - Created complete session info")
                        return self._build_final_session_info(session_info_raw)
                        
            except Exception as e:
                logger.debug(f"Direct WeekendInfo access failed: {e}")
            
            # Fallback: Try other methods if direct access fails
            session_info_raw = None
            
            # Method 2: Force check if session info update is available
            if hasattr(self.ir, 'session_info_update'):
                try:
                    # Force check for session info updates
                    update_available = self.ir.session_info_update
                    if update_available:
                        logger.info("🔄 Session info update detected - forcing refresh")
                    
                    # Get fresh session info
                    session_info_raw = getattr(self.ir, 'session_info', None)
                    if session_info_raw:
                        logger.info(f"✅ Got fresh session info via method 2: {type(session_info_raw)}")
                except Exception as e:
                    logger.debug(f"Method 2 (with update check) failed: {e}")
            
            # Method 3: Direct session_info attribute  
            if not session_info_raw and self.available_methods.get('session_info', {}).get('exists'):
                try:
                    session_info_raw = getattr(self.ir, 'session_info', None)
                    if session_info_raw:
                        logger.debug(f"Got session info via method 3: {type(session_info_raw)}")
                except Exception as e:
                    logger.debug(f"Method 3 failed: {e}")
            
            # Method 4: get_session_info method  
            if not session_info_raw and self.available_methods.get('get_session_info', {}).get('callable'):
                try:
                    session_info_raw = self.ir.get_session_info()
                    if session_info_raw:
                        logger.debug(f"Got session info via method 4: {type(session_info_raw)}")
                except Exception as e:
                    logger.debug(f"Method 4 failed: {e}")
            
            # Method 5: Try session_info_update approach
            if not session_info_raw and hasattr(self.ir, 'get_session_info_update_by_key'):
                try:
                    # Try to get each section separately
                    for section in ['DriverInfo', 'WeekendInfo', 'SessionInfo']:
                        section_data = self.ir.get_session_info_update_by_key(section)
                        if section_data:
                            logger.debug(f"Got {section} via method 5: {type(section_data)}")
                            # If we get any section, we can build from there
                            if not session_info_raw:
                                session_info_raw = {}
                            session_info_raw[section] = section_data
                except Exception as e:
                    logger.debug(f"Method 5 failed: {e}")
            
            # Method 6: Try enhanced telemetry approach for track info
            if not session_info_raw or (session_info_raw and 
                session_info_raw.get('WeekendInfo', {}).get('TrackDisplayName') in ['iRacing Track', None]):
                try:
                    logger.info("🧪 ENHANCED SESSION MODE: Trying all possible track extraction methods")
                    
                    # Try to get track info directly from telemetry in Test Drive mode
                    test_track_name = self.safe_get_telemetry('TrackDisplayName')
                    test_track_config = self.safe_get_telemetry('TrackConfigName') 
                    test_track_id = self.safe_get_telemetry('TrackID')
                    test_track_length = self.safe_get_telemetry('TrackLength')
                    
                    # Try additional telemetry fields that might contain track info
                    track_name_short = self.safe_get_telemetry('TrackDisplayNameShort')
                    track_config_short = self.safe_get_telemetry('TrackConfigNameShort')
                    track_city = self.safe_get_telemetry('TrackCity')
                    track_country = self.safe_get_telemetry('TrackCountry')
                    
                    logger.info(f"🧪 ENHANCED SESSION - ALL telemetry track fields:")
                    logger.info(f"🧪 ENHANCED SESSION -   TrackDisplayName: '{test_track_name}'")
                    logger.info(f"🧪 ENHANCED SESSION -   TrackConfigName: '{test_track_config}'")
                    logger.info(f"🧪 ENHANCED SESSION -   TrackDisplayNameShort: '{track_name_short}'")
                    logger.info(f"🧪 ENHANCED SESSION -   TrackConfigNameShort: '{track_config_short}'")
                    logger.info(f"🧪 ENHANCED SESSION -   TrackCity: '{track_city}'")
                    logger.info(f"🧪 ENHANCED SESSION -   TrackCountry: '{track_country}'")
                    logger.info(f"🧪 ENHANCED SESSION -   TrackID: '{test_track_id}'")
                    logger.info(f"🧪 ENHANCED SESSION -   TrackLength: '{test_track_length}'")
                    
                    # Try to get session type info
                    session_type = self.safe_get_telemetry('SessionType')
                    session_sub_type = self.safe_get_telemetry('SessionSubType')
                    session_name = self.safe_get_telemetry('SessionName')
                    
                    logger.info(f"🧪 ENHANCED SESSION - Session info:")
                    logger.info(f"🧪 ENHANCED SESSION -   SessionType: '{session_type}'")
                    logger.info(f"🧪 ENHANCED SESSION -   SessionSubType: '{session_sub_type}'")
                    logger.info(f"🧪 ENHANCED SESSION -   SessionName: '{session_name}'")
                    
                    # Determine the best track name to use
                    real_track_name = None
                    
                    # Priority order: full name > short name > city/country combo
                    if test_track_name and test_track_name not in ['iRacing Track', '', None]:
                        real_track_name = test_track_name
                        logger.info(f"🎯 ENHANCED SESSION - Using TrackDisplayName: {real_track_name}")
                    elif track_name_short and track_name_short not in ['iRacing Track', '', None]:
                        real_track_name = track_name_short
                        logger.info(f"🎯 ENHANCED SESSION - Using TrackDisplayNameShort: {real_track_name}")
                    elif track_city and track_country:
                        real_track_name = f"{track_city} ({track_country})"
                        logger.info(f"🎯 ENHANCED SESSION - Using City/Country: {real_track_name}")
                    
                    # If we found real track data via telemetry, create session info
                    if real_track_name:
                        logger.info(f"🎯 ENHANCED SESSION - Found real track via telemetry: {real_track_name}")
                        
                        # Build comprehensive track config name
                        real_config_name = test_track_config or track_config_short or ''
                        
                        session_info_raw = {
                            'WeekendInfo': {
                                'TrackDisplayName': real_track_name,
                                'TrackConfigName': real_config_name,
                                'TrackCity': track_city or 'Unknown',
                                'TrackCountry': track_country or 'Unknown',
                                'TrackID': test_track_id or 0,
                                'TrackLength': f"{test_track_length:.2f} km" if test_track_length else '0.00 km'
                            },
                            'SessionInfo': {
                                'Sessions': [{
                                    'SessionName': session_name or 'Time Attack',
                                    'SessionType': session_type or 'Time Attack',
                                    'SessionSubType': session_sub_type or ''
                                }]
                            }
                        }
                        logger.info(f"✅ ENHANCED SESSION - Created session info from telemetry")
                    else:
                        logger.warning(f"❌ ENHANCED SESSION - No real track data found in any telemetry field")
                        
                except Exception as e:
                    logger.debug(f"Method 6 (enhanced telemetry) failed: {e}")
            
            # Parse session info if we have it as a string (YAML format)
            if session_info_raw and isinstance(session_info_raw, str):
                try:
                    import yaml
                    session_info_raw = yaml.safe_load(session_info_raw)
                    logger.debug("Successfully parsed session info YAML")
                except ImportError:
                    logger.debug("PyYAML not available, trying JSON parse")
                    try:
                        import json
                        session_info_raw = json.loads(session_info_raw)
                        logger.debug("Successfully parsed session info JSON")
                    except:
                        logger.debug("Could not parse session info as JSON or YAML")
                        session_info_raw = None
                except Exception as e:
                    logger.debug(f"Could not parse session info string: {e}")
                    session_info_raw = None
            
            return self._build_final_session_info(session_info_raw)
            
        except Exception as e:
            logger.warning(f"Session info unavailable: {e}")
            # Return minimal fallback structure
            return {
                'WeekendInfo': {'TrackDisplayName': 'iRacing Track', 'TrackConfigName': ''},
                'DriverInfo': {'Drivers': [{'CarScreenName': 'Race Car', 'CarIdx': 0}]},
                'SessionInfo': {'Sessions': [{'SessionName': 'Practice'}]}
            }
    
    def _build_final_session_info(self, session_info_raw):
        """Helper method to build final session info structure"""
        
        # Try to get real car name from DriverInfo structure (CORRECT METHOD)
        real_car_name = None
        car_screen_name_short = None
        car_path = None
        
        try:
            # Access DriverInfo the correct way and find the current player's driver
            driver_info = self.ir['DriverInfo']
            if driver_info and 'Drivers' in driver_info and len(driver_info['Drivers']) > 0:
                # Get the player's car index to find the right driver
                player_car_idx = driver_info.get('DriverCarIdx')
                logger.info(f"🔍 CAR DEBUG - Player car index: {player_car_idx}")
                logger.info(f"🔍 CAR DEBUG - Total drivers: {len(driver_info['Drivers'])}")
                
                # Find the player's driver entry
                player_driver = None
                for driver in driver_info['Drivers']:
                    car_idx = driver.get('CarIdx')
                    logger.debug(f"🔍 CAR DEBUG - Checking driver CarIdx {car_idx} vs player {player_car_idx}")
                    if car_idx == player_car_idx:
                        player_driver = driver
                        logger.info(f"🔍 CAR DEBUG - Found player driver at CarIdx {car_idx}")
                        break
                
                if player_driver:
                    real_car_name = player_driver.get('CarScreenName', '')
                    car_screen_name_short = player_driver.get('CarScreenNameShort', '')
                    car_path = player_driver.get('CarPath', '')
                    logger.info(f"🔍 CAR DEBUG - Successfully found player's car data")
                    logger.info(f"🔍 CAR DEBUG -   CarScreenName: '{real_car_name}'")
                    logger.info(f"🔍 CAR DEBUG -   CarScreenNameShort: '{car_screen_name_short}'")
                    logger.info(f"🔍 CAR DEBUG -   CarPath: '{car_path}'")
                else:
                    logger.warning(f"🔍 CAR DEBUG - Could not find player driver with CarIdx {player_car_idx}")
                    # Fallback: use first driver if player not found
                    if len(driver_info['Drivers']) > 0:
                        driver_data = driver_info['Drivers'][0]
                        real_car_name = driver_data.get('CarScreenName', '')
                        car_screen_name_short = driver_data.get('CarScreenNameShort', '')
                        car_path = driver_data.get('CarPath', '')
                        logger.warning(f"🔍 CAR DEBUG - Using fallback driver at index 0")
            else:
                logger.warning(f"🔍 CAR DEBUG - DriverInfo structure missing or empty")
        except Exception as e:
            logger.warning(f"🔍 CAR DEBUG - Could not access DriverInfo structure: {e}")
            
            # Fallback: Try telemetry fields as backup
            real_car_name = self.safe_get_telemetry('CarScreenName')
            car_screen_name_short = self.safe_get_telemetry('CarScreenNameShort')
            car_path = self.safe_get_telemetry('CarPath')
            logger.info(f"🔍 CAR DEBUG - Fallback to telemetry fields:")
            logger.info(f"� CAR DEBUG -   CarScreenName: '{real_car_name}'")
            logger.info(f"🔍 CAR DEBUG -   CarScreenNameShort: '{car_screen_name_short}'")
            logger.info(f"🔍 CAR DEBUG -   CarPath: '{car_path}'")
        
        # Try multiple car name sources in priority order
        if real_car_name and real_car_name not in ['GT3 Car', 'Race Car', '', None]:
            default_car_name = real_car_name
            logger.info(f"🚗 SUCCESS! Using real CarScreenName: '{default_car_name}'")
        elif car_screen_name_short and car_screen_name_short not in ['GT3 Car', 'Race Car', '', None]:
            default_car_name = car_screen_name_short
            logger.info(f"🚗 SUCCESS! Using real CarScreenNameShort: '{default_car_name}'")
        else:
            default_car_name = 'GT3 Car'
            logger.warning(f"🚗 Falling back to generic name: '{default_car_name}' (no real car data found)")
        
        logger.info(f"🚗 Building session info with car name: '{default_car_name}'")
        
        # Create comprehensive session info structure
        basic_session_info = {
            'WeekendInfo': {
                'TrackDisplayName': 'iRacing Track',
                'TrackConfigName': '',
                'TrackID': 0,
                'TrackLength': '0.00 km',
                'TrackCity': 'Unknown',
                'TrackCountry': 'Unknown'
            },
            'DriverInfo': {
                'DriverCarIdx': 0,
                'Drivers': [{
                    'CarIdx': 0,
                    'CarScreenName': default_car_name,
                    'CarPath': 'gt3',
                    'CarID': 0,
                    'CarClassShortName': 'GT3'
                }]
            },
            'SessionInfo': {
                'Sessions': [{
                    'SessionName': 'Practice',
                    'SessionType': 'Practice'
                }]
            }
        }
        
        # If we have real session info, merge it with our structure
        if session_info_raw and isinstance(session_info_raw, dict):
            try:
                logger.info(f"🔍 SESSION DEBUG - RAW session_info_raw object:")
                logger.info(f"🔍 SESSION DEBUG - {json.dumps(session_info_raw, indent=2, default=str)}")
                
                # Update with real data if available
                if 'WeekendInfo' in session_info_raw:
                    logger.info(f"🔍 SESSION DEBUG - Found WeekendInfo in session_info_raw:")
                    for key, value in session_info_raw['WeekendInfo'].items():
                        logger.info(f"🔍 SESSION DEBUG -   {key}: '{value}'")
                    basic_session_info['WeekendInfo'].update(session_info_raw['WeekendInfo'])
                    logger.info(f"✅ Updated WeekendInfo from session data: {session_info_raw['WeekendInfo'].get('TrackDisplayName', 'No track name')}")
                if 'DriverInfo' in session_info_raw:
                    basic_session_info['DriverInfo'].update(session_info_raw['DriverInfo'])
                    logger.debug(f"Updated DriverInfo from session data")
                if 'SessionInfo' in session_info_raw:
                    basic_session_info['SessionInfo'].update(session_info_raw['SessionInfo'])
                    logger.debug(f"Updated SessionInfo from session data")
            except Exception as e:
                logger.debug(f"Could not merge session info: {e}")
        else:
            logger.debug("No valid session info found, using enhanced defaults")
        
        # Enhance defaults with telemetry data if available (only if still generic)
        try:
            player_car_class = self.safe_get_telemetry('PlayerCarClass')
            if player_car_class is not None:
                # Update car info based on telemetry only if we still have generic names
                drivers = basic_session_info['DriverInfo']['Drivers']
                if drivers and len(drivers) > 0:
                    current_car_name = drivers[0]['CarScreenName']
                    # ONLY enhance if we have truly generic names - don't override real car names
                    if current_car_name in ['GT3 Car', 'Race Car', 'GT3 Class Car', 'GTE Class Car', 'LMP2 Class Car']:
                        # Only enhance if we have generic names - try real car name first
                        if real_car_name and real_car_name not in ['GT3 Car', 'Race Car', 'GT3 Class Car']:
                            drivers[0]['CarScreenName'] = real_car_name
                            logger.info(f"✅ Enhanced car name with real DriverInfo data: {real_car_name}")
                        else:
                            # Last resort: use class-based names only if no real name available
                            class_names = {
                                0: 'GT3 Class Car',
                                1: 'GTE Class Car', 
                                2: 'LMP2 Class Car',
                                3: 'LMP1 Class Car',
                                4: 'Formula Class Car'
                            }
                            fallback_name = class_names.get(player_car_class, f'Class {player_car_class} Car')
                            drivers[0]['CarScreenName'] = fallback_name
                            drivers[0]['CarClassShortName'] = f'Class {player_car_class}'
                            logger.info(f"🔄 Using class fallback: {fallback_name}")
                    else:
                        logger.info(f"🚗 Keeping real car name (not enhancing): '{current_car_name}'")
                        
                        # Update class name if we have real data
                        real_car_class = self.safe_get_telemetry('CarClassShortName')
                        if real_car_class:
                            drivers[0]['CarClassShortName'] = real_car_class
                        
        except Exception as e:
            logger.debug(f"Could not enhance session info with telemetry: {e}")
        
        logger.info(f"🔍 SESSION DEBUG - FINAL basic_session_info object:")
        logger.info(f"🔍 SESSION DEBUG - {json.dumps(basic_session_info, indent=2, default=str)}")
        
        return basic_session_info
    
    # =============================================================================
    # SECTION 1: TELEMETRY DATA METHODS - Real-time car performance data
    # =============================================================================
    
    def get_telemetry_data_clean(self) -> Optional[Dict[str, Any]]:
        """Get pure telemetry data only - no session or driver info mixed in"""
        try:
            telemetry = {}
            
            # Core telemetry fields for GT3 coaching
            telemetry_fields = {
                # Session data
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
                
                # Delta timing (iRacing native deltas)
                'lapDeltaToBestLap': 'LapDeltaToBestLap',
                'lapDeltaToOptimalLap': 'LapDeltaToOptimalLap',
                'lapDeltaToSessionBestLap': 'LapDeltaToSessionBestLap',
                
                # Position and race data
                'position': 'Position',
                'classPosition': 'ClassPosition',
                
                # Track and car status
                'playerTrackSurface': 'PlayerTrackSurface',
                
                # Vehicle dynamics for oversteer/understeer detection
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
                
                # Fuel (converted from liters to gallons for US display)
                'fuelLevel': 'FuelLevel',
                'fuelLevelPct': 'FuelLevelPct',
                'fuelUsePerHour': 'FuelUsePerHour',
                
                # Pit and track status
                'onPitRoad': 'OnPitRoad',
            }
            
            # Get basic telemetry
            for field_name, irsdk_key in telemetry_fields.items():
                value = self.safe_get_telemetry(irsdk_key)
                if value is not None:
                    # Convert speed from m/s to MPH
                    if field_name == 'speed':
                        value = value * 2.23694
                    # Convert throttle and brake from 0-1 to 0-100 percentage
                    elif field_name in ['throttle', 'brake']:
                        value = value * 100
                    # Convert fuel from liters to gallons
                    elif field_name in ['fuelLevel', 'fuelUsePerHour']:
                        value = value * 0.264172
                    
                    telemetry[field_name] = value
            
            # Calculate delta time
            on_pit_road = self.safe_get_telemetry('OnPitRoad')
            native_delta = None
            
            # Try different delta fields in order of preference
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
                # Fallback: calculate delta if native isn't available
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
            
            # Get tire pressures
            tire_pressure_mapping = {
                'tirePressureLF': 'LFTirePres',
                'tirePressureRF': 'RFTirePres',
                'tirePressureLR': 'LRTirePres', 
                'tirePressureRR': 'RRTirePres'
            }
            
            for display_name, irsdk_key in tire_pressure_mapping.items():
                pressure = self.safe_get_telemetry(irsdk_key)
                if pressure is not None:
                    telemetry[display_name] = pressure
            
            return telemetry if telemetry else None
                
        except Exception as e:
            logger.error(f"Error getting telemetry data: {e}")
            return None
    
    # =============================================================================
    # SECTION 2: SESSION & DRIVER DATA METHODS - Track and car information
    # =============================================================================
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get track/session information only"""
        try:
            # Try to get track info from WeekendInfo (most reliable)
            track_name = "Unknown Track"
            track_config = ""
            
            if self.last_session_info:
                weekend_info = self.last_session_info.get('WeekendInfo', {})
                track_display_name = weekend_info.get('TrackDisplayName', '')
                track_config_name = weekend_info.get('TrackConfigName', '')
                
                if track_display_name and track_display_name not in ['iRacing Track', '']:
                    track_name = track_display_name
                    track_config = track_config_name or ""
                    logger.debug(f"✅ Track from session: {track_name}")
                else:
                    logger.debug(f"❌ Session track name rejected: '{track_display_name}'")
            
            # Fallback to telemetry if session info isn't available
            if track_name == "Unknown Track":
                track_display_name = self.safe_get_telemetry('TrackDisplayName')
                track_config_name = self.safe_get_telemetry('TrackConfigName')
                if track_display_name and track_display_name not in ['iRacing Track', '']:
                    track_name = track_display_name
                    track_config = track_config_name or ""
                    logger.debug(f"✅ Track from telemetry: {track_name}")
            
            # Build full track name
            full_track_name = track_name
            if track_config and track_config.strip():
                full_track_name += f" - {track_config}"
            
            return {
                'trackName': track_name,
                'trackConfig': track_config,
                'fullTrackName': full_track_name,
                'trackDisplayName': track_name,  # For backward compatibility
                'trackConfigName': track_config  # For backward compatibility
            }
            
        except Exception as e:
            logger.error(f"Error getting session data: {e}")
            return {
                'trackName': "Unknown Track",
                'trackConfig': "",
                'fullTrackName': "Unknown Track",
                'trackDisplayName': "Unknown Track",
                'trackConfigName': ""
            }
    
    def get_driver_data(self) -> Dict[str, Any]:
        """Get driver/car information only"""
        try:
            car_name = "Unknown Car"
            
            # Try to get car name from DriverInfo (most reliable)
            try:
                driver_info = self.ir['DriverInfo']
                if driver_info and 'Drivers' in driver_info and len(driver_info['Drivers']) > 0:
                    player_car_idx = driver_info.get('DriverCarIdx')
                    
                    # Find the player's driver entry
                    player_driver = None
                    for driver in driver_info['Drivers']:
                        if driver.get('CarIdx') == player_car_idx:
                            player_driver = driver
                            break
                    
                    if player_driver:
                        driver_car_name = player_driver.get('CarScreenName', '')
                        if driver_car_name and driver_car_name not in ['GT3 Car', 'Race Car', '']:
                            car_name = driver_car_name
                            logger.debug(f"✅ Car from live DriverInfo: {car_name}")
                    else:
                        # Fallback to first driver
                        if len(driver_info['Drivers']) > 0:
                            driver_car_name = driver_info['Drivers'][0].get('CarScreenName', '')
                            if driver_car_name and driver_car_name not in ['GT3 Car', 'Race Car', '']:
                                car_name = driver_car_name
                                logger.debug(f"✅ Car from fallback DriverInfo: {car_name}")
            except Exception as e:
                logger.debug(f"Could not get car from live DriverInfo: {e}")
            
            # Try cached session info if live DriverInfo didn't work
            if car_name == "Unknown Car" and self.last_session_info:
                try:
                    driver_info = self.last_session_info.get('DriverInfo', {})
                    drivers = driver_info.get('Drivers', [])
                    if drivers and len(drivers) > 0:
                        driver_car_name = drivers[0].get('CarScreenName', '')
                        if driver_car_name and driver_car_name not in ['GT3 Car', 'Race Car', '']:
                            car_name = driver_car_name
                            logger.debug(f"✅ Car from cached DriverInfo: {car_name}")
                except Exception as e:
                    logger.debug(f"Could not get car from cached DriverInfo: {e}")
            
            # Final fallback to telemetry
            if car_name == "Unknown Car":
                car_screen_name = self.safe_get_telemetry('CarScreenName')
                if car_screen_name and car_screen_name not in ['GT3 Car', 'Race Car', '']:
                    car_name = car_screen_name
                    logger.debug(f"✅ Car from telemetry: {car_name}")
                else:
                    car_screen_name_short = self.safe_get_telemetry('CarScreenNameShort')
                    if car_screen_name_short and car_screen_name_short not in ['GT3 Car', 'Race Car', '']:
                        car_name = car_screen_name_short
                        logger.debug(f"✅ Car from telemetry short: {car_name}")
            
            return {
                'carName': car_name,
                'driverCarName': car_name  # For backward compatibility
            }
            
        except Exception as e:
            logger.error(f"Error getting driver data: {e}")
            return {
                'carName': "Unknown Car",
                'driverCarName': "Unknown Car"
            }
    
    # =============================================================================
    # SECTION 3: COMBINED DATA METHODS - For backward compatibility
    # =============================================================================
    
    def _reset_session_cache(self):
        """Reset session cache when session changes"""
        self._cached_track_name = None
        self._cached_car_name = None
        self._session_cache_valid = False
        logger.info("🔄 Session cache reset - will re-extract on next telemetry")
    
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
            # First, ensure SDK is started
            if hasattr(self.ir, 'startup') and hasattr(self.ir, 'is_initialized'):
                try:
                    # Check if is_initialized is callable or a property
                    if self.available_methods.get('is_initialized', {}).get('callable'):
                        initialized = self.ir.is_initialized()
                    else:
                        initialized = self.ir.is_initialized
                        
                    if not initialized:
                        logger.debug("SDK not initialized, attempting startup...")
                        startup_result = self.ir.startup()
                        if not startup_result:
                            logger.debug("SDK startup failed")
                            return False
                except Exception as e:
                    logger.debug(f"Error checking initialization: {e}")
                    return False
            
            # Check connection status
            if hasattr(self.ir, 'is_connected') and hasattr(self.ir, 'is_initialized'):
                try:
                    # Check if methods are callable or properties
                    if self.available_methods.get('is_connected', {}).get('callable'):
                        connected = self.ir.is_connected()
                    else:
                        connected = self.ir.is_connected
                        
                    if self.available_methods.get('is_initialized', {}).get('callable'):
                        initialized = self.ir.is_initialized()
                    else:
                        initialized = self.ir.is_initialized
                        
                    logger.debug(f"Connection status: connected={connected}, initialized={initialized}")
                    return connected and initialized
                except Exception as e:
                    logger.debug(f"Error calling connection methods: {e}")
            
            # Fallback: Test by getting data
            test_data = self.safe_get_telemetry('SessionTime')
            is_connected = test_data is not None
            logger.debug(f"Connection test via telemetry: {is_connected} (SessionTime: {test_data})")
            return is_connected
            
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False
    

    async def get_telemetry_data(self) -> Optional[Dict[str, Any]]:
        """Get combined telemetry data with session and driver info"""
        try:
            # Get pure telemetry data
            telemetry = self.get_telemetry_data_clean()
            if not telemetry:
                return None
            
            # Get session data
            session_data = self.get_session_data()
            
            # Get driver data  
            driver_data = self.get_driver_data()
            
            # Combine all data for the complete telemetry package
            combined_data = {
                **telemetry,
                **session_data,
                **driver_data
            }
            
            # Log the session info being sent (this should show real data now)
            logger.debug(f"Session info from telemetry: track='{combined_data.get('trackName', 'Unknown')}', car='{combined_data.get('carName', 'Unknown')}'")
            
            return combined_data
                
        except Exception as e:
            logger.error(f"Error getting combined telemetry data: {e}")
            return None

    async def telemetry_loop(self):
        """Main telemetry collection and broadcasting loop"""
        last_telemetry_time = 0
        last_session_info_time = 0
        session_info_update_interval = 5.0  # Update session info every 5 seconds
        
        while True:
            try:
                # Check connection and update connection status 
                if not self.check_connection_status():
                    if self.is_connected_to_iracing:
                        logger.info("❌ Lost connection to iRacing")
                        self.is_connected_to_iracing = False
                        await self.broadcast_to_clients({
                            "type": "Telemetry",
                            "data": {"isConnected": False},
                            "isConnected": False
                        })
                    await asyncio.sleep(2)  # Check more frequently when disconnected
                    continue
                
                if not self.is_connected_to_iracing:
                    logger.info("✅ Connected to iRacing!")
                    self.is_connected_to_iracing = True
                
                # Get session info periodically (every 5 seconds) to get fresh WeekendInfo
                current_time = time.time()
                if current_time - last_session_info_time >= session_info_update_interval:
                    session_info = self.get_session_info()
                    if session_info:
                        # Check if session has changed (reset cache if needed)
                        old_track = self.last_session_info.get('WeekendInfo', {}).get('TrackDisplayName', '') if self.last_session_info else ''
                        new_track = session_info.get('WeekendInfo', {}).get('TrackDisplayName', '')
                        
                        # Only reset cache if we're changing from one real track to another real track
                        # Don't reset when going from empty/placeholder to real track
                        if (old_track != new_track and 
                            old_track not in ['', 'iRacing Track'] and 
                            new_track not in ['iRacing Track', '']):
                            logger.info(f"🔄 Session change detected: '{old_track}' → '{new_track}' - resetting cache")
                            self._reset_session_cache()
                        elif old_track == '' and new_track not in ['iRacing Track', '']:
                            logger.info(f"🏁 Initial session detected: '{new_track}' - keeping existing cache")
                        
                        self.last_session_info = session_info
                        
                        # Update session info with real-time car name from telemetry
                        real_car_name = self.safe_get_telemetry('CarScreenName')
                        if real_car_name and real_car_name not in ['GT3 Car', 'Race Car', '']:
                            # Update the DriverInfo with real car name
                            if 'DriverInfo' in self.last_session_info and 'Drivers' in self.last_session_info['DriverInfo']:
                                drivers = self.last_session_info['DriverInfo']['Drivers']
                                if drivers and len(drivers) > 0:
                                    old_name = drivers[0].get('CarScreenName', 'Unknown')
                                    drivers[0]['CarScreenName'] = real_car_name
                                    logger.info(f"✅ Updated session info car name: '{old_name}' → '{real_car_name}'")
                        
                        # Print the ENTIRE last_session_info object for debugging
                        logger.info(f"🔍 SESSION DEBUG - COMPLETE last_session_info object:")
                        logger.info(f"🔍 SESSION DEBUG - {json.dumps(self.last_session_info, indent=2, default=str)}")
                        
                        # Check if we're in a real session with actual track data
                        weekend_info = session_info.get('WeekendInfo', {})
                        track_name = weekend_info.get('TrackDisplayName', '')
                        track_config = weekend_info.get('TrackConfigName', '')
                        
                        logger.info(f"🔍 SESSION DEBUG - WeekendInfo ALL KEY-VALUE PAIRS:")
                        for key, value in weekend_info.items():
                            logger.info(f"🔍 SESSION DEBUG -   {key}: '{value}'")
                        
                        # Determine session status
                        if track_name and track_name not in ['iRacing Track', '']:
                            full_track_name = track_name
                            if track_config and track_config.strip():
                                full_track_name += f" - {track_config}"
                            logger.info(f"🏁 ✅ REAL TRACK SESSION: {full_track_name}")
                            logger.info(f"🎯 Track data available - coaching can provide track-specific advice")
                        elif track_name == 'iRacing Track':
                            logger.info(f"⚠️  PLACEHOLDER SESSION: Connected to iRacing but not in a real session")
                            logger.info(f"💡 To get real track names: Join a practice session, test drive, or race")
                            logger.info(f"🔧 Current data is generic placeholder - track-specific coaching limited")
                        else:
                            logger.info(f"❌ NO TRACK DATA: No session info available")
                        
                        # Broadcast updated session info to all UI clients
                        await self.broadcast_to_clients({
                            "type": "SessionInfo",
                            "data": self.last_session_info
                        })
                        
                        logger.debug(f"🔄 Updated and broadcast session info to UI clients")
                    else:
                        logger.warning(f"❌ No session info returned from get_session_info()")
                    last_session_info_time = current_time
                    
                telemetry = await self.get_telemetry_data()
                
                # Always try to send to coaching server, even if telemetry is None
                # The coaching server can handle this and update session state
                await self.send_to_coaching_server(telemetry)
                
                if telemetry:
                    # Add connection status to telemetry data
                    telemetry['isConnected'] = True
                    self.last_telemetry = telemetry
                    
                    # Log PaceFlags when they change (no converter errors!)
                    if 'paceFlags' in telemetry and telemetry['paceFlags'] != 0:
                        logger.debug(f"🏁 PaceFlags: {telemetry['paceFlags']}")
                    
                    await self.broadcast_to_clients({
                        "type": "Telemetry",
                        "data": telemetry,
                        "isConnected": True
                    })
                    
                    # Log successful telemetry occasionally
                    current_time = time.time()
                    if current_time - last_telemetry_time > 10:  # Every 10 seconds
                        logger.info(f"� Telemetry streaming (Speed: {telemetry.get('speed', 0):.1f} mph, RPM: {telemetry.get('rpm', 0):.0f})")
                        
                        # Note: Tire and brake temperature logging removed since iRacing doesn't provide reliable data
                        
                        # Debug AI coaching status
                        if 'coachingMessage' in telemetry:
                            logger.info(f"🤖 AI Coach: {telemetry['coachingMessage']} (P{telemetry.get('coachingPriority', 'N/A')})")
                        
                        last_telemetry_time = current_time
                
                # Update at 60Hz for responsive GT3 coaching
                await asyncio.sleep(1/60)
                
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                await asyncio.sleep(1)
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"🚀 Starting GT3 telemetry server on {self.host}:{self.port}")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f"✅ GT3 telemetry server running on ws://{self.host}:{self.port}")
            logger.info("🎯 Waiting for iRacing and GT3 AI Coaching to connect...")
            logger.info("💡 Start iRacing and go to any session to begin telemetry streaming")
            
            # Start the telemetry collection loop
            await self.telemetry_loop()

    async def send_to_coaching_server(self, telemetry_data):
        """Send telemetry data to coaching server for AI processing"""
        try:
            # Connect to coaching server if not connected
            if self.coaching_server_ws is None:
                import websockets
                try:
                    # Connect to coaching server's telemetry endpoint
                    logger.info("🔄 Attempting to connect to coaching server at ws://localhost:8083...")
                    self.coaching_server_ws = await websockets.connect("ws://localhost:8083")
                    logger.info("📤 ✅ SUCCESS! Connected to coaching server for telemetry data")
                except Exception as e:
                    logger.error(f"❌ FAILED to connect to coaching server: {e}")
                    logger.error(f"❌ Make sure coaching server is running on port 8083")
                    return
            
            # Send telemetry data to coaching server
            message = {
                "type": "telemetry_data",
                "data": telemetry_data,
                "timestamp": telemetry_data.get('sessionTime', 0)
            }
            
            await self.coaching_server_ws.send(json.dumps(message))
            logger.info("📤 Sent telemetry data to coaching server")
            
        except Exception as e:
            logger.error(f"❌ Error sending to coaching server: {e}")
            # Reset connection on error
            self.coaching_server_ws = None

    def _cache_valid_session_info(self, track_name: str, car_name: str):
        """Cache valid session info to avoid re-extraction"""
        if track_name and track_name not in ['Unknown Track', 'iRacing Track', '']:
            if not self._cached_track_name or self._cached_track_name != track_name:
                self._cached_track_name = track_name
                logger.info(f"🔒 CACHED track name: '{track_name}'")
        
        if car_name and car_name not in ['Unknown Car', 'GT3 Car', 'Race Car', '']:
            if not self._cached_car_name or self._cached_car_name != car_name:
                self._cached_car_name = car_name
                logger.info(f"🔒 CACHED car name: '{car_name}'")
        
        # Mark cache as valid if we have both
        if self._cached_track_name and self._cached_car_name:
            self._session_cache_valid = True
            logger.info(f"✅ SESSION CACHE COMPLETE: Track='{self._cached_track_name}', Car='{self._cached_car_name}'")
    
    def _get_cached_or_extract_names(self, telemetry: Dict[str, Any]) -> tuple:
        """Get cached session info or extract if not cached - DEPRECATED: Use get_session_data() and get_driver_data()"""
        # For backward compatibility only
        session_data = self.get_session_data()
        driver_data = self.get_driver_data()
        return session_data['trackName'], driver_data['carName']

def main():
    server = GT3TelemetryServer()
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("🏁 GT3 telemetry server stopped by user")

if __name__ == "__main__":
    main()