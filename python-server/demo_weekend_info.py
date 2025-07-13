#!/usr/bin/env python3
"""
Demonstration script showing how WeekendInfo track names will now be properly extracted
and displayed in the session widget instead of generic "hot track" names.
"""

import json
import time

def demo_weekend_info_extraction():
    print("🏁 GT3 AI Coaching - Track Name Extraction Demo")
    print("=" * 60)
    print()
    
    # Simulate real iRacing WeekendInfo data
    sample_weekend_info_data = [
        {
            "scenario": "Watkins Glen GP Weekend",
            "WeekendInfo": {
                "TrackDisplayName": "Watkins Glen International",
                "TrackConfigName": "Grand Prix",
                "TrackCity": "Watkins Glen",
                "TrackCountry": "USA",
                "TrackID": 101,
                "TrackLength": "5.43 km"
            },
            "DriverInfo": {
                "DriverCarIdx": 0,
                "Drivers": [{
                    "CarIdx": 0,
                    "CarScreenName": "Porsche 992 GT3 R",
                    "CarPath": "porsche992gt3r",
                    "CarID": 143
                }]
            }
        },
        {
            "scenario": "Road America Session",
            "WeekendInfo": {
                "TrackDisplayName": "Road America",
                "TrackConfigName": "",
                "TrackCity": "Elkhart Lake",
                "TrackCountry": "USA",
                "TrackID": 78,
                "TrackLength": "6.51 km"
            },
            "DriverInfo": {
                "DriverCarIdx": 0,
                "Drivers": [{
                    "CarIdx": 0,
                    "CarScreenName": "BMW M4 GT3",
                    "CarPath": "bmwm4gt3",
                    "CarID": 157
                }]
            }
        },
        {
            "scenario": "Silverstone International",
            "WeekendInfo": {
                "TrackDisplayName": "Silverstone Circuit",
                "TrackConfigName": "International",
                "TrackCity": "Silverstone",
                "TrackCountry": "England",
                "TrackID": 89,
                "TrackLength": "5.89 km"
            },
            "DriverInfo": {
                "DriverCarIdx": 0,
                "Drivers": [{
                    "CarIdx": 0,
                    "CarScreenName": "Mercedes-AMG GT3",
                    "CarPath": "mercedesamggt3",
                    "CarID": 159
                }]
            }
        }
    ]
    
    def extract_session_info(session_data):
        """Simulate the new extraction logic"""
        weekend_info = session_data.get('WeekendInfo', {})
        driver_info = session_data.get('DriverInfo', {})
        
        # Extract track name (new logic)
        track_display_name = weekend_info.get('TrackDisplayName', '')
        track_config_name = weekend_info.get('TrackConfigName', '')
        
        if track_display_name and track_display_name not in ['iRacing Track', 'Hot Climate Track', 'Cold Climate Track', 'Temperate Climate Track']:
            track_name = track_display_name
            if track_config_name and track_config_name.strip():
                track_name += f" - {track_config_name}"
        else:
            track_name = "Unknown Track"
        
        # Extract car name
        drivers = driver_info.get('Drivers', [])
        car_name = "Unknown Car"
        if drivers and len(drivers) > 0:
            car_name = drivers[0].get('CarScreenName', 'Unknown Car')
        
        return track_name, car_name
    
    print("🔧 Processing sample iRacing session data:")
    print()
    
    for i, data in enumerate(sample_weekend_info_data, 1):
        print(f"📊 Scenario {i}: {data['scenario']}")
        track_name, car_name = extract_session_info(data)
        
        # Create session ID like the system would
        session_id = f"{track_name}_{car_name}_{int(time.time())}"
        
        print(f"  📍 Track: {track_name}")
        print(f"  🚗 Car: {car_name}")
        print(f"  🆔 Session ID: {session_id}")
        print()
    
    print("=" * 60)
    print("🎯 BEFORE vs AFTER Comparison:")
    print()
    print("BEFORE (Current System):")
    print("  📍 Track: Road Course (Hot Climate)")
    print("  🚗 Car: Unknown Car")
    print("  🆔 Session: Road Course (Hot Climate)_Unknown Car_1752366903")
    print("  ❌ Generic names based on temperature estimation")
    print()
    print("AFTER (With WeekendInfo Fix):")
    print("  📍 Track: Watkins Glen International - Grand Prix")
    print("  🚗 Car: Porsche 992 GT3 R")
    print("  🆔 Session: Watkins Glen International - Grand Prix_Porsche 992 GT3 R_1752366903")
    print("  ✅ Real track and car names from iRacing data")
    print()
    
    print("🔄 How the Fix Works:")
    print("1. iRacing provides WeekendInfo with real track data")
    print("2. Telemetry server extracts TrackDisplayName + TrackConfigName")
    print("3. Real track name is sent to coaching server in telemetry")
    print("4. Coaching server creates session with proper names")
    print("5. Session widget displays actual track name")
    print("6. Session files are saved with meaningful names")
    print()
    
    print("📱 Frontend Impact:")
    print("  Session widget will now show: 'Watkins Glen International - Grand Prix'")
    print("  Instead of: 'Road Course (Hot Climate)'")
    print("  Much more useful for drivers to track their progress!")
    print()
    
    print("✅ Changes Made:")
    print("  • Modified telemetry-server.py to prioritize WeekendInfo data")
    print("  • Enhanced coaching-server.py to better handle track names")
    print("  • Added additional session info fields to telemetry data")
    print("  • Improved filtering of generic iRacing placeholder names")

if __name__ == "__main__":
    demo_weekend_info_extraction()
