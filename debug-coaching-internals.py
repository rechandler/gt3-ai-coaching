"""
Coaching Service Diagnostic - Check internal data flow
"""
import asyncio
import json
import logging
import time
import sys
import os

# Add the services path
sys.path.append(os.path.join(os.path.dirname(__file__), 'telemetry-server', 'services'))

async def test_coaching_service_internals():
    """Test if coaching service is receiving data from telemetry service"""
    print("🔍 Coaching Service Internal Diagnostic")
    print("=" * 60)
    
    # Check if coaching service can connect to telemetry streams
    print("\n📊 Testing Coaching Service → Telemetry Service Connection")
    
    try:
        import websockets
        
        # Test telemetry stream connection (same as coaching service does)
        print("  Testing telemetry stream connection...")
        async with websockets.connect("ws://localhost:9001") as ws:
            print("  ✅ Can connect to telemetry stream")
            
            # Listen for a few messages
            message_count = 0
            for _ in range(5):
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(message)
                    message_count += 1
                    
                    if data.get('type') == 'telemetry':
                        print(f"  📈 Received telemetry message #{message_count}")
                        telemetry_data = data.get('data', {})
                        print(f"    Speed: {telemetry_data.get('speed', 'N/A')}")
                        print(f"    Connected: {telemetry_data.get('isConnected', 'N/A')}")
                        break
                except asyncio.TimeoutError:
                    continue
            
            if message_count == 0:
                print("  ❌ No messages received from telemetry stream")
            
    except Exception as e:
        print(f"  ❌ Failed to connect to telemetry stream: {e}")
        return
    
    # Test session stream
    print("\n🏁 Testing session stream connection...")
    try:
        async with websockets.connect("ws://localhost:9002") as ws:
            print("  ✅ Can connect to session stream")
            
            message_count = 0
            for _ in range(3):
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(message)
                    message_count += 1
                    
                    if data.get('type') == 'session':
                        print(f"  🏎️  Received session message #{message_count}")
                        session_data = data.get('data', {})
                        print(f"    Track: {session_data.get('trackName', 'N/A')}")
                        break
                except asyncio.TimeoutError:
                    continue
                    
    except Exception as e:
        print(f"  ❌ Failed to connect to session stream: {e}")
    
    # Check coaching service logs by connecting and monitoring
    print("\n🧠 Testing UI endpoint behavior...")
    
    try:
        async with websockets.connect("ws://localhost:8082") as ws:
            print("  ✅ Connected to coaching service UI endpoint")
            
            received_types = []
            start_time = time.time()
            
            # Monitor for 5 seconds
            while time.time() - start_time < 5:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(message)
                    msg_type = data.get('type', 'unknown')
                    received_types.append(msg_type)
                    
                    if msg_type == 'telemetry':
                        print(f"  ✅ TELEMETRY FORWARDED! Data keys: {list(data.get('data', {}).keys())}")
                        return
                    else:
                        print(f"  📨 Received: {msg_type}")
                        
                except asyncio.TimeoutError:
                    continue
            
            print(f"\n  📊 Summary: Received {len(received_types)} messages")
            unique_types = set(received_types)
            for msg_type in unique_types:
                count = received_types.count(msg_type)
                print(f"    {msg_type}: {count}")
            
            if 'telemetry' not in unique_types:
                print("\n  ❌ ISSUE: No telemetry messages forwarded to UI")
                print("     This suggests the coaching service is not receiving")
                print("     telemetry data from the telemetry service, OR")
                print("     there's an issue in the forwarding logic.")
            
    except Exception as e:
        print(f"  ❌ Failed to test UI endpoint: {e}")

if __name__ == "__main__":
    asyncio.run(test_coaching_service_internals())
