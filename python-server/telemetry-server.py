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
            # Try multiple methods to get session info
            session_info_raw = None
            
            # Method 1: Direct session_info attribute
            if self.available_methods.get('session_info', {}).get('exists'):
                try:
                    session_info_raw = getattr(self.ir, 'session_info', None)
                    if session_info_raw:
                        logger.debug(f"Got session info via method 1: {type(session_info_raw)}")
                except Exception as e:
                    logger.debug(f"Method 1 failed: {e}")
            
            # Method 2: get_session_info method  
            if not session_info_raw and self.available_methods.get('get_session_info', {}).get('callable'):
                try:
                    session_info_raw = self.ir.get_session_info()
                    if session_info_raw:
                        logger.debug(f"Got session info via method 2: {type(session_info_raw)}")
                except Exception as e:
                    logger.debug(f"Method 2 failed: {e}")
            
            # Method 3: Try session_info_update approach
            if not session_info_raw and hasattr(self.ir, 'get_session_info_update_by_key'):
                try:
                    # Try to get each section separately
                    for section in ['DriverInfo', 'WeekendInfo', 'SessionInfo']:
                        section_data = self.ir.get_session_info_update_by_key(section)
                        if section_data:
                            logger.debug(f"Got {section} via method 3: {type(section_data)}")
                            # If we get any section, we can build from there
                            if not session_info_raw:
                                session_info_raw = {}
                            session_info_raw[section] = section_data
                except Exception as e:
                    logger.debug(f"Method 3 failed: {e}")
            
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
                        'CarScreenName': 'GT3 Car',
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
                    # Update with real data if available
                    if 'WeekendInfo' in session_info_raw:
                        basic_session_info['WeekendInfo'].update(session_info_raw['WeekendInfo'])
                        logger.debug(f"Updated WeekendInfo from session data")
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
            
            # Enhance defaults with telemetry data if available
            try:
                player_car_class = self.safe_get_telemetry('PlayerCarClass')
                if player_car_class is not None:
                    # Update car info based on telemetry
                    drivers = basic_session_info['DriverInfo']['Drivers']
                    if drivers and len(drivers) > 0:
                        if drivers[0]['CarScreenName'] == 'GT3 Car':
                            # Enhance with class-specific names
                            class_names = {
                                0: 'GT3 Class Car',
                                1: 'GTE Class Car', 
                                2: 'LMP2 Class Car',
                                3: 'LMP1 Class Car',
                                4: 'Formula Class Car'
                            }
                            drivers[0]['CarScreenName'] = class_names.get(player_car_class, f'Class {player_car_class} Car')
                            drivers[0]['CarClassShortName'] = f'Class {player_car_class}'
                            
                track_temp = self.safe_get_telemetry('TrackTemp')
                if track_temp is not None:
                    # Enhance track info based on temperature
                    if basic_session_info['WeekendInfo']['TrackDisplayName'] == 'iRacing Track':
                        if track_temp > 35:
                            basic_session_info['WeekendInfo']['TrackDisplayName'] = 'Hot Climate Track'
                            basic_session_info['WeekendInfo']['TrackCountry'] = 'Warm Region'
                        elif track_temp < 15:
                            basic_session_info['WeekendInfo']['TrackDisplayName'] = 'Cold Climate Track'
                            basic_session_info['WeekendInfo']['TrackCountry'] = 'Cool Region'
                        else:
                            basic_session_info['WeekendInfo']['TrackDisplayName'] = 'Temperate Climate Track'
                            basic_session_info['WeekendInfo']['TrackCountry'] = 'Moderate Region'
                            
            except Exception as e:
                logger.debug(f"Could not enhance session info with telemetry: {e}")
            
            return basic_session_info
            
        except Exception as e:
            logger.warning(f"Session info unavailable: {e}")
            # Return minimal fallback structure
            return {
                'WeekendInfo': {'TrackDisplayName': 'iRacing Track', 'TrackConfigName': ''},
                'DriverInfo': {'Drivers': [{'CarScreenName': 'Race Car', 'CarIdx': 0}]},
                'SessionInfo': {'Sessions': [{'SessionName': 'Practice'}]}
            }
    
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
        """Get telemetry data - focus on core GT3 coaching data"""
        try:
            telemetry = {}
            data_count = 0
            
            # Core telemetry fields for GT3 coaching
            telemetry_fields = {
                # Session data
                'sessionTime': 'SessionTime',
                'sessionTick': 'SessionTick', 
                'sessionFlags': 'SessionFlags',
                'sessionState': 'SessionState',  # Add session state
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
                'playerTrackSurface': 'PlayerTrackSurface',  # Add track surface
                
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
                        value = value * 2.23694  # Convert m/s to MPH
                    # Convert throttle and brake from 0-1 to 0-100 percentage
                    elif field_name in ['throttle', 'brake']:
                        value = value * 100  # Convert to percentage
                    # Convert fuel from liters to gallons (iRacing uses liters internally)
                    elif field_name in ['fuelLevel', 'fuelUsePerHour']:
                        value = value * 0.264172  # Convert liters to US gallons
                    # fuelLevelPct is already a percentage (0-1), keep as-is
                    telemetry[field_name] = value
                    data_count += 1
            
            # Use iRacing's native delta time (preferred) or calculate fallback
            on_pit_road = self.safe_get_telemetry('OnPitRoad')
            
            # Try to use iRacing's native delta fields (most accurate)
            native_delta = None
            
            # Try different delta fields in order of preference
            delta_fields = ['LapDeltaToBestLap', 'LapDeltaToOptimalLap', 'LapDeltaToSessionBestLap']
            for delta_field in delta_fields:
                delta_value = self.safe_get_telemetry(delta_field)
                if delta_value is not None and abs(delta_value) < 999:  # Valid delta (not 999+ invalid value)
                    native_delta = delta_value
                    logger.debug(f"Using native delta from {delta_field}: {delta_value:.3f}")
                    break
            
            # Set delta time
            if not on_pit_road and native_delta is not None:
                telemetry['deltaTime'] = native_delta
                telemetry['deltaSource'] = 'iRacing_native'
                data_count += 1
            elif not on_pit_road:
                # Fallback: calculate delta if native isn't available
                current_lap_time = self.safe_get_telemetry('LapCurrentLapTime')
                best_lap_time = self.safe_get_telemetry('LapBestLapTime')
                
                if (current_lap_time is not None and best_lap_time is not None and best_lap_time > 0):
                    telemetry['deltaTime'] = current_lap_time - best_lap_time
                    telemetry['deltaSource'] = 'calculated_fallback'
                    logger.debug(f"Using calculated delta: {telemetry['deltaTime']:.3f}")
                    data_count += 1
                else:
                    telemetry['deltaTime'] = None
                    telemetry['deltaSource'] = 'unavailable'
                    data_count += 1
            else:
                # In pits - don't show delta
                telemetry['deltaTime'] = None
                telemetry['deltaSource'] = 'in_pits'
                logger.debug("In pits - delta time disabled")
                data_count += 1
            
            # Get car and track information - improved fallback system
            car_name = "Unknown Car"
            track_name = "Unknown Track"
            
            # First, try to get car/track info from telemetry data directly
            try:
                # Try to get car name from telemetry
                car_screen_name = self.safe_get_telemetry('CarScreenName')
                if car_screen_name:
                    car_name = car_screen_name
                    logger.info(f"✅ Car name from telemetry: {car_name}")
                else:
                    # Try alternative car name fields
                    car_screen_name_short = self.safe_get_telemetry('CarScreenNameShort')
                    if car_screen_name_short:
                        car_name = car_screen_name_short
                        logger.info(f"✅ Car name from telemetry (short): {car_name}")
                
                # Try to get track name from telemetry
                track_display_name = self.safe_get_telemetry('TrackDisplayName')
                track_config_name = self.safe_get_telemetry('TrackConfigName')
                if track_display_name:
                    track_name = track_display_name
                    if track_config_name:
                        track_name += f" - {track_config_name}"
                    logger.info(f"✅ Track name from telemetry: {track_name}")
                else:
                    # Try alternative track name fields
                    track_name_short = self.safe_get_telemetry('TrackDisplayNameShort')
                    if track_name_short:
                        track_name = track_name_short
                        logger.info(f"✅ Track name from telemetry (short): {track_name}")
                        
            except Exception as e:
                logger.debug(f"Could not get car/track from telemetry: {e}")
            
            # Fallback to session info if telemetry didn't provide car/track info
            if (car_name == "Unknown Car" or track_name == "Unknown Track") and self.last_session_info:
                try:
                    # Extract car name from session info
                    if car_name == "Unknown Car":
                        driver_info = self.last_session_info.get('DriverInfo', {})
                        drivers = driver_info.get('Drivers', [])
                        if drivers and len(drivers) > 0:
                            session_car_name = drivers[0].get('CarScreenName', '')
                            if session_car_name and session_car_name != 'GT3 Car':
                                car_name = session_car_name
                                logger.debug(f"Car name from session info: {car_name}")
                    
                    # Extract track name from session info
                    if track_name == "Unknown Track":
                        weekend_info = self.last_session_info.get('WeekendInfo', {})
                        track_display_name = weekend_info.get('TrackDisplayName', '')
                        track_config_name = weekend_info.get('TrackConfigName', '')
                        if track_display_name and track_display_name != 'iRacing Track':
                            track_name = f"{track_display_name}"
                            if track_config_name:
                                track_name += f" - {track_config_name}"
                            logger.debug(f"Track name from session info: {track_name}")
                except Exception as e:
                    logger.debug(f"Could not extract car/track info from session: {e}")
            
            # Enhanced fallback system using telemetry data patterns
            if car_name == "Unknown Car":
                try:
                    player_car_class = self.safe_get_telemetry('PlayerCarClass')
                    if player_car_class is not None:
                        # Car class mapping for common iRacing classes
                        car_class_names = {
                            0: "GT3 Car",  # Common GT3 class
                            1: "GTE Car",
                            2: "LMP2 Car", 
                            3: "LMP1 Car",
                            4: "Formula Car",
                            5: "Stock Car",
                            6: "Touring Car",
                            7: "Sports Car",
                            8: "Prototype Car"
                        }
                        car_name = car_class_names.get(player_car_class, f"Car Class {player_car_class}")
                        logger.info(f"🔄 Using car class fallback: {car_name}")
                        
                        # For GT3 class, try to be more specific based on telemetry signature
                        if player_car_class == 0:  # GT3 class
                            rpm = self.safe_get_telemetry('RPM')
                            max_gear = self.safe_get_telemetry('Gear')
                            if rpm and max_gear:
                                # Simple heuristics based on common GT3 cars
                                if rpm > 8000:
                                    car_name = "Ferrari 488 GT3 (estimated)"
                                elif rpm > 7500:
                                    car_name = "Porsche 911 GT3 R (estimated)"
                                elif rpm > 7000:
                                    car_name = "Mercedes AMG GT3 (estimated)"
                                else:
                                    car_name = "BMW M4 GT3 (estimated)"
                                logger.info(f"🎯 GT3 car estimation: {car_name}")
                except Exception as e:
                    logger.debug(f"Could not determine car from class: {e}")
            
            # Enhanced track fallback using track characteristics
            if track_name == "Unknown Track":
                try:
                    track_temp = self.safe_get_telemetry('TrackTemp')
                    track_surface = self.safe_get_telemetry('PlayerTrackSurface')
                    track_wetness = self.safe_get_telemetry('TrackWetness')
                    
                    if track_temp is not None:
                        if track_temp > 40:
                            track_name = "Road Course (Hot Climate)"
                        elif track_temp < 15:
                            track_name = "Road Course (Cold Climate)"
                        else:
                            track_name = "Road Course"
                        
                        if track_wetness and track_wetness == 2:
                            track_name += " (Wet)"
                        elif track_wetness and track_wetness == 3:
                            track_name += " (Very Wet)"
                        
                        logger.info(f"🌍 Track estimation based on conditions: {track_name}")
                except Exception as e:
                    logger.debug(f"Could not estimate track: {e}")
            
            telemetry['carName'] = car_name
            telemetry['trackName'] = track_name
            
            # Send telemetry to coaching server for AI processing
            await self.send_to_coaching_server(telemetry)
            
            # Remove any coaching-related fields from telemetry before sending to UI
            # Telemetry should be pure car/track data only
            telemetry_clean = {k: v for k, v in telemetry.items() 
                             if not k.startswith('coaching') and k not in ['secondaryMessages', 'improvementPotential', 'userProfile']}
            
            # Use clean telemetry for the rest of the function
            telemetry = telemetry_clean
            # Note: Tire temperature collection removed - iRacing doesn't provide reliable
            # tire temperature data during racing through iRSDK
            
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
                    data_count += 1
            
            # Note: Brake temperature collection removed - iRacing doesn't provide reliable
            # brake temperature data during racing through iRSDK
            
            # Return the completed telemetry data
            if data_count > 0:
                logger.debug(f"✅ Returning telemetry with {data_count} fields")
                return telemetry
            else:
                logger.debug("❌ No telemetry data available")
                return None
                
        except Exception as e:
            logger.error(f"Error getting telemetry data: {e}")
            return None

    async def telemetry_loop(self):
        """Main telemetry collection and broadcasting loop"""
        last_telemetry_time = 0
        
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
                
                # Get telemetry and session info
                telemetry = await self.get_telemetry_data()
                session_info = self.get_session_info()
                
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
        # For now, we'll let the coaching server connect directly to us
        # This method is kept for future enhancements
        pass

def main():
    server = GT3TelemetryServer()
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("🏁 GT3 telemetry server stopped by user")

if __name__ == "__main__":
    main()