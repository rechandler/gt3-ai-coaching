"""
Mock iRSDK for testing and development without iRacing
"""

import random
import time
import math

class MockIRSDK:
    """Mock implementation of iRSDK for testing without iRacing"""
    
    def __init__(self):
        self.is_initialized = True
        self.is_connected = True
        self._startup_called = False
        self._start_time = time.time()
        
        # Mock session data
        self._current_track = "Fuji Speedway"
        self._current_config = "Grand Prix"
        self._current_car = "Chevrolet Corvette Z06 GT3.R"
        
        # Mock telemetry state
        self._lap_time = 0
        self._lap_distance = 0
        self._last_lap_time = 115.2  # Sample lap time
        self._best_lap_time = 114.8
        
    def startup(self):
        """Mock startup method"""
        self._startup_called = True
        return True
    
    def shutdown(self):
        """Mock shutdown method"""
        return True
    
    def __getitem__(self, key):
        """Mock telemetry data access"""
        current_time = time.time() - self._start_time
        
        # Create realistic mock data based on time
        if key == 'SessionTime':
            return current_time
        elif key == 'SessionTick':
            return int(current_time * 60)  # 60 Hz
        elif key == 'Speed':
            # Simulate varying speed
            base_speed = 50 + 30 * math.sin(current_time * 0.1)
            return max(0, base_speed / 2.23694)  # Convert mph to m/s
        elif key == 'RPM':
            return 6000 + 2000 * math.sin(current_time * 0.2)
        elif key == 'Gear':
            return random.randint(3, 6)
        elif key == 'Throttle':
            return random.uniform(0.3, 1.0)
        elif key == 'Brake':
            return random.uniform(0, 0.3) if random.random() < 0.2 else 0
        elif key == 'SteeringWheelAngle':
            return math.sin(current_time * 0.15) * 0.5
        elif key == 'LapCurrentLapTime':
            self._lap_time = (current_time % 120)  # 2 minute laps
            return self._lap_time
        elif key == 'LapLastLapTime':
            return self._last_lap_time
        elif key == 'LapBestLapTime':
            return self._best_lap_time
        elif key == 'LapDistPct':
            return (current_time % 120) / 120
        elif key == 'Lap':
            return int(current_time / 120) + 1
        elif key == 'LapDeltaToBestLap':
            if self._lap_time > 0:
                return self._lap_time - self._best_lap_time
            return 0
        elif key == 'Position':
            return 3
        elif key == 'ClassPosition':
            return 2
        elif key == 'PlayerTrackSurface':
            return 1  # On track
        elif key == 'OnPitRoad':
            return False
        elif key == 'FuelLevel':
            return 45.2  # Liters
        elif key == 'FuelLevelPct':
            return 0.75
        elif key == 'TrackDisplayName':
            return self._current_track
        elif key == 'TrackConfigName':
            return self._current_config
        elif key == 'CarScreenName':
            return self._current_car
        elif key == 'WeekendInfo':
            return {
                'TrackDisplayName': self._current_track,
                'TrackConfigName': self._current_config,
                'EventType': 'Practice'
            }
        elif key == 'DriverInfo':
            return {
                'DriverCarIdx': 0,
                'Drivers': [{
                    'CarIdx': 0,
                    'CarScreenName': self._current_car,
                    'UserName': 'Mock Driver'
                }]
            }
        elif key in ['YawRate', 'Yaw', 'Roll', 'RollRate', 'Pitch', 'PitchRate']:
            return random.uniform(-0.5, 0.5)
        elif key in ['VelocityX', 'VelocityY', 'VelocityZ']:
            return random.uniform(-50, 50)
        elif key in ['LatAccel', 'LongAccel', 'VertAccel']:
            return random.uniform(-20, 20)
        elif key == 'SteeringWheelTorque':
            return random.uniform(-10, 10)
        elif key in ['TrackTempCrew', 'AirTemp']:
            return 25.0  # Celsius
        elif key == 'WeatherType':
            return 0  # Clear
        elif key == 'FuelUsePerHour':
            return 150.0  # Liters per hour
        elif key in ['LFTirePres', 'RFTirePres', 'LRTirePres', 'RRTirePres']:
            return 27.5 + random.uniform(-1, 1)  # PSI
        elif key in ['SessionFlags', 'SessionState', 'PaceFlags']:
            return 0
        else:
            return None
    
    @property 
    def session_info(self):
        """Mock session info property"""
        return {
            'WeekendInfo': {
                'TrackDisplayName': self._current_track,
                'TrackConfigName': self._current_config,
                'EventType': 'Practice'
            },
            'DriverInfo': {
                'DriverCarIdx': 0,
                'Drivers': [{
                    'CarIdx': 0,
                    'CarScreenName': self._current_car,
                    'UserName': 'Mock Driver'
                }]
            },
            'SessionInfo': {
                'Sessions': [{
                    'SessionName': 'Practice',
                    'SessionType': 'Practice'
                }]
            }
        }
    
    @property
    def session_info_update(self):
        """Mock session info update flag"""
        return True

# Create the IRSDK class as an alias for compatibility
IRSDK = MockIRSDK
