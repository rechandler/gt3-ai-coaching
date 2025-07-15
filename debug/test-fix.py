"""
Test if the coaching service fix works
"""
import asyncio
import json
import time

async def test_telemetry_forwarding():
    """Test if telemetry data is now being forwarded properly"""
    print("🔧 Testing Telemetry Forwarding Fix")
    print("=" * 50)
    
    try:
        import websockets
        
        print("🧠 Connecting to coaching service...")
        async with websockets.connect("ws://localhost:8082") as ws:
            print("✅ Connected to coaching service UI endpoint")
            
            start_time = time.time()
            telemetry_received = False
            message_count = 0
            
            # Wait up to 15 seconds for telemetry data
            while time.time() - start_time < 15 and not telemetry_received:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(message)
                    message_count += 1
                    
                    msg_type = data.get('type', 'unknown')
                    print(f"📨 Message {message_count}: {msg_type}")
                    
                    if msg_type == 'telemetry':
                        print("🎉 SUCCESS! Telemetry data is now being forwarded!")
                        telemetry_data = data.get('data', {})
                        print(f"   Speed: {telemetry_data.get('speed', 'N/A')}")
                        print(f"   RPM: {telemetry_data.get('rpm', 'N/A')}")
                        print(f"   Connected: {telemetry_data.get('isConnected', 'N/A')}")
                        print(f"   Data keys: {list(telemetry_data.keys())}")
                        telemetry_received = True
                        break
                        
                except asyncio.TimeoutError:
                    print("⏳ Waiting for telemetry data...")
                    continue
            
            if not telemetry_received:
                print("❌ Still not receiving telemetry data")
                print("   The coaching service may need to be restarted")
                print("   to pick up the fix.")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_telemetry_forwarding())
