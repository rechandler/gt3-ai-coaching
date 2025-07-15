"""
Detailed debugging tool to see exact message contents
"""
import asyncio
import json
import websockets

async def test_detailed():
    print("Detailed message inspection...")
    
    # Test telemetry stream
    try:
        uri = "ws://localhost:9001"
        print(f"\nConnecting to telemetry stream at {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to telemetry stream!")
            
            message_count = 0
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'telemetry':
                        print(f"\n📊 Telemetry data structure:")
                        telemetry = data.get('data', {})
                        print(json.dumps(telemetry, indent=2))
                        break
                    message_count += 1
                    if message_count >= 5:
                        break
                        
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
    except Exception as e:
        print(f"❌ Telemetry stream error: {e}")

if __name__ == "__main__":
    asyncio.run(test_detailed())
