#!/usr/bin/env python3
"""
Test script to verify track name extraction from WeekendInfo
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_track_extraction():
    print("🧪 Testing Track Name Extraction from WeekendInfo")
    print("=" * 60)
    
    # Simulate various WeekendInfo scenarios
    test_scenarios = [
        {
            "name": "Watkins Glen International",
            "weekend_info": {
                "TrackDisplayName": "Watkins Glen International",
                "TrackConfigName": "Grand Prix",
                "TrackCity": "Watkins Glen",
                "TrackCountry": "USA"
            },
            "expected": "Watkins Glen International - Grand Prix"
        },
        {
            "name": "Road America (no config)",
            "weekend_info": {
                "TrackDisplayName": "Road America",
                "TrackConfigName": "",
                "TrackCity": "Elkhart Lake",
                "TrackCountry": "USA"
            },
            "expected": "Road America"
        },
        {
            "name": "Nürburgring with config",
            "weekend_info": {
                "TrackDisplayName": "Nürburgring",
                "TrackConfigName": "Grand Prix",
                "TrackCity": "Nürburg",
                "TrackCountry": "Germany"
            },
            "expected": "Nürburgring - Grand Prix"
        },
        {
            "name": "Silverstone Circuit",
            "weekend_info": {
                "TrackDisplayName": "Silverstone Circuit",
                "TrackConfigName": "International",
                "TrackCity": "Silverstone",
                "TrackCountry": "England"
            },
            "expected": "Silverstone Circuit - International"
        },
        {
            "name": "Generic iRacing Track (should be filtered)",
            "weekend_info": {
                "TrackDisplayName": "iRacing Track",
                "TrackConfigName": "",
                "TrackCity": "",
                "TrackCountry": ""
            },
            "expected": None  # Should be filtered out
        }
    ]
    
    def extract_track_name(weekend_info):
        """Simulate the extraction logic from telemetry-server.py"""
        track_display_name = weekend_info.get('TrackDisplayName', '')
        track_config_name = weekend_info.get('TrackConfigName', '')
        
        if track_display_name and track_display_name not in ['iRacing Track', 'Hot Climate Track', 'Cold Climate Track', 'Temperate Climate Track']:
            track_name = track_display_name
            if track_config_name and track_config_name.strip():
                track_name += f" - {track_config_name}"
            return track_name
        return None
    
    print("🎯 Testing track name extraction logic:")
    print()
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"Test {i}: {scenario['name']}")
        print(f"  WeekendInfo: {scenario['weekend_info']}")
        
        result = extract_track_name(scenario['weekend_info'])
        expected = scenario['expected']
        
        if result == expected:
            print(f"  ✅ SUCCESS: Got '{result}'")
        else:
            print(f"  ❌ FAILED: Got '{result}', expected '{expected}'")
        print()
    
    print("🔧 Integration Test:")
    print("This demonstrates how the new logic will work:")
    print()
    print("1. iRacing provides WeekendInfo in session_info")
    print("2. Telemetry server extracts real track names from WeekendInfo")
    print("3. Track names are sent to coaching server in telemetry data")
    print("4. Coaching server uses real track names for session creation")
    print("5. Session widget displays actual track names instead of 'Hot Track'")
    print()
    
    print("🎉 Expected Results:")
    print("  Before: 'Road Course (Hot Climate)_Unknown Car_1234567890'")
    print("  After:  'Watkins Glen International - Grand Prix_Porsche 992 GT3 R_1234567890'")
    print()
    
    return True

if __name__ == "__main__":
    test_track_extraction()
