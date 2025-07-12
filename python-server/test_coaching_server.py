#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to simulate telemetry data for coaching server
"""

import asyncio
import json
import websockets
import time

async def simulate_telemetry():
    """Simulate telemetry data being sent to coaching server"""
    uri = "ws://localhost:8081"  # Telemetry server port that coaching server expects
    
    # Sample telemetry data
    telemetry_data = {
        "type": "Telemetry",
        "data": {
            # Core telemetry
            "speed": 85.5,
            "rpm": 6500,
            "gear": 4,
            "throttle": 75.0,
            "brake": 0.0,
            "lapCurrentLapTime": 87.5,
            "lapLastLapTime": 89.2,
            "lap": 3,
            "position": 5,
            
            # Track/car info that gets extracted from telemetry but is inconsistent
            "trackDisplayName": "Unstable Track Name From Telemetry",
            "trackName": "Changing Track Name",
            "carName": "Estimated Car From Telemetry", 
            "driverCarName": "Another Car Name Variant",
            
            # Session info
            "sessionState": 4,  # Racing
            "sessionFlags": 0,
            "onPitRoad": False,
            "playerTrackSurface": 4  # On track
        }
    }
    
    print("🚀 Starting telemetry simulation...")
    print(f"📊 Will send telemetry with inconsistent track/car names:")
    print(f"   Track: {telemetry_data['data']['trackDisplayName']}")
    print(f"   Car: {telemetry_data['data']['carName']}")
    print()
    
    try:
        # Start a simple WebSocket server on port 8081
        async def handle_coaching_connection(websocket, path=None):
            print("🔗 Coaching server connected to our telemetry simulator")
            
            # Send initial telemetry data repeatedly
            for i in range(10):
                # Vary the telemetry slightly each time
                telemetry_data["data"]["speed"] = 85.5 + (i * 2)
                telemetry_data["data"]["lapCurrentLapTime"] = 87.5 + i
                telemetry_data["data"]["lap"] = 3 + (i // 3)
                
                # Change track/car names to show inconsistency
                if i % 3 == 0:
                    telemetry_data["data"]["trackDisplayName"] = "Track Name Variant A"
                    telemetry_data["data"]["carName"] = "Car Estimate A"
                elif i % 3 == 1:
                    telemetry_data["data"]["trackDisplayName"] = "Track Name Variant B"  
                    telemetry_data["data"]["carName"] = "Car Estimate B"
                else:
                    telemetry_data["data"]["trackDisplayName"] = "Track Name Variant C"
                    telemetry_data["data"]["carName"] = "Car Estimate C"
                
                await websocket.send(json.dumps(telemetry_data))
                print(f"📡 Sent telemetry #{i+1} - Track: {telemetry_data['data']['trackDisplayName'][:20]}...")
                await asyncio.sleep(2)  # Send every 2 seconds
            
            print("✅ Telemetry simulation completed")
        
        # Start the server
        server = await websockets.serve(handle_coaching_connection, "localhost", 8081)
        print("📡 Telemetry simulator running on ws://localhost:8081")
        print("⏳ Waiting for coaching server to connect...")
        
        # Keep running
        await asyncio.Future()  # Run forever
        
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped")
    except Exception as e:
        print(f"❌ Error in telemetry simulation: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_telemetry())
