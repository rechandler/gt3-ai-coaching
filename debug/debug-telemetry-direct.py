"""
Test connection directly to the telemetry service ports
"""
import asyncio
import json
import websockets

async def test_telemetry_service():
    print("Testing telemetry service connections...")
    
    # Test telemetry stream (port 9001)
    try:
        uri = "ws://localhost:9001"
        print(f"\nConnecting to telemetry stream at {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to telemetry stream!")
            
            message_count = 0
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"📊 Telemetry message {message_count + 1}: {data.get('type', 'unknown')}")
                    if data.get('type') == 'telemetry':
                        telemetry = data.get('data', {})
                        print(f"   Speed: {telemetry.get('Speed', 'N/A')}")
                        print(f"   RPM: {telemetry.get('RPM', 'N/A')}")
                    
                    message_count += 1
                    if message_count >= 3:
                        break
                        
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
    except Exception as e:
        print(f"❌ Telemetry stream error: {e}")
    
    # Test session stream (port 9002)
    try:
        uri = "ws://localhost:9002"
        print(f"\nConnecting to session stream at {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to session stream!")
            
            message_count = 0
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"🏁 Session message {message_count + 1}: {data.get('type', 'unknown')}")
                    if data.get('type') == 'session':
                        session = data.get('data', {})
                        print(f"   Track: {session.get('trackName', 'N/A')}")
                        print(f"   Car: {session.get('carName', 'N/A')}")
                    
                    message_count += 1
                    if message_count >= 3:
                        break
                        
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
    except Exception as e:
        print(f"❌ Session stream error: {e}")

if __name__ == "__main__":
    asyncio.run(test_telemetry_service())
