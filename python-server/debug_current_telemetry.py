#!/usr/bin/env python3
"""
Debug script to see current telemetry values and analysis status
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def monitor_telemetry():
    """Monitor current telemetry and show key values"""
    uri = "ws://localhost:8083"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("🔍 Connected to telemetry server - monitoring data...")
            
            sample_count = 0
            while sample_count < 10:  # Show 10 samples
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    if data.get('type') == 'telemetry_data':
                        tel = data['data']
                        sample_count += 1
                        
                        print(f"\n=== SAMPLE {sample_count} ===")
                        print(f"Speed: {tel.get('Speed', 0):.1f} mph")
                        print(f"SessionState: {tel.get('SessionState', 'Unknown')}")
                        print(f"IsOnTrack: {tel.get('IsOnTrack', False)}")
                        print(f"Throttle: {tel.get('Throttle', 0):.3f}")
                        print(f"Brake: {tel.get('Brake', 0):.3f}")
                        print(f"Steering: {tel.get('SteeringWheelAngle', 0):.3f}")
                        print(f"Gear: {tel.get('Gear', 0)}")
                        print(f"RPM: {tel.get('RPM', 0):.0f}")
                        print(f"TrackName: {tel.get('TrackDisplayName', 'Unknown')}")
                        print(f"CarName: {tel.get('CarScreenName', 'Unknown')}")
                        print("---")
                        
                except asyncio.TimeoutError:
                    logger.warning("⏰ Timeout waiting for telemetry data")
                    break
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    break
                    
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(monitor_telemetry())
