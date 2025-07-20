"""
Simple debugging tool to check telemetry service connections
"""
import asyncio
import json
import websockets

async def test_connection():
    try:
        # Test connection to coaching data service
        uri = "ws://localhost:8083"
        print(f"Connecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Listen for a few messages
            print("Listening for messages...")
            message_count = 0
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"\n📨 Message {message_count + 1}:")
                    print(f"   Type: {data.get('type', 'unknown')}")
                    print(f"   Data keys: {list(data.get('data', {}).keys()) if data.get('data') else 'none'}")
                    
                    if data.get('type') == 'telemetry':
                        telemetry = data.get('data', {})
                        print(f"   Speed: {telemetry.get('Speed', 'N/A')}")
                        print(f"   Connected: {telemetry.get('isConnected', 'N/A')}")
                        print(f"   Session Active: {telemetry.get('sessionActive', 'N/A')}")
                    
                    message_count += 1
                    if message_count >= 5:
                        break
                        
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON: {message[:100]}...")
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    
    except ConnectionRefusedError:
        print("❌ Connection refused - is the coaching data service running?")
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
