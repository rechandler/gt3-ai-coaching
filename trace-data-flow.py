"""
Data Flow Tracer - Follows telemetry data through the entire pipeline
"""
import asyncio
import json
import websockets
import time

async def trace_data_flow():
    """Trace data flow from telemetry service to coaching service"""
    print("🔍 Tracing data flow through the pipeline...")
    print("=" * 60)
    
    # Listen to telemetry service directly
    print("\n📊 Step 1: Raw Telemetry Service (Port 9001)")
    try:
        async with websockets.connect("ws://localhost:9001") as telemetry_ws:
            print("✅ Connected to telemetry service")
            
            # Get a few telemetry messages
            telemetry_count = 0
            for _ in range(3):
                try:
                    message = await asyncio.wait_for(telemetry_ws.recv(), timeout=2.0)
                    data = json.loads(message)
                    if data.get('type') == 'telemetry':
                        telemetry_count += 1
                        telemetry_data = data.get('data', {})
                        print(f"  📈 Telemetry #{telemetry_count}:")
                        print(f"    Speed: {telemetry_data.get('speed', 'N/A')}")
                        print(f"    RPM: {telemetry_data.get('rpm', 'N/A')}")
                        print(f"    Connected: {telemetry_data.get('isConnected', 'N/A')}")
                        break
                except asyncio.TimeoutError:
                    continue
                    
            if telemetry_count == 0:
                print("  ⚠️  No telemetry data received")
                
    except Exception as e:
        print(f"  ❌ Failed to connect to telemetry: {e}")
        return
    
    # Listen to session service
    print("\n🏁 Step 2: Session Service (Port 9002)")
    try:
        async with websockets.connect("ws://localhost:9002") as session_ws:
            print("✅ Connected to session service")
            
            session_count = 0
            for _ in range(3):
                try:
                    message = await asyncio.wait_for(session_ws.recv(), timeout=2.0)
                    data = json.loads(message)
                    if data.get('type') == 'session':
                        session_count += 1
                        session_data = data.get('data', {})
                        print(f"  🏎️  Session #{session_count}:")
                        print(f"    Track: {session_data.get('trackName', 'N/A')}")
                        print(f"    Car: {session_data.get('carName', 'N/A')}")
                        break
                except asyncio.TimeoutError:
                    continue
                    
            if session_count == 0:
                print("  ⚠️  No session data received")
                
    except Exception as e:
        print(f"  ❌ Failed to connect to session: {e}")
    
    # Listen to coaching service (what UI sees)
    print("\n🧠 Step 3: Coaching Service Output (Port 8082)")
    try:
        async with websockets.connect("ws://localhost:8082") as coaching_ws:
            print("✅ Connected to coaching service (UI endpoint)")
            
            received_messages = []
            start_time = time.time()
            
            # Collect messages for 10 seconds
            while time.time() - start_time < 10:
                try:
                    message = await asyncio.wait_for(coaching_ws.recv(), timeout=1.0)
                    data = json.loads(message)
                    received_messages.append(data)
                    
                    msg_type = data.get('type', 'unknown')
                    print(f"  📨 Received: {msg_type}")
                    
                    if msg_type == 'telemetry':
                        telemetry_data = data.get('data', {})
                        print(f"    ✅ TELEMETRY DATA FLOWING!")
                        print(f"    Speed: {telemetry_data.get('speed', 'N/A')}")
                        print(f"    RPM: {telemetry_data.get('rpm', 'N/A')}")
                        print(f"    Connected: {telemetry_data.get('isConnected', 'N/A')}")
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
            # Summarize what we received
            message_types = [msg.get('type', 'unknown') for msg in received_messages]
            unique_types = set(message_types)
            
            print(f"\n📊 Summary - Received {len(received_messages)} messages:")
            for msg_type in unique_types:
                count = message_types.count(msg_type)
                print(f"  {msg_type}: {count} messages")
            
            if 'telemetry' not in unique_types:
                print("\n❌ ISSUE FOUND: No telemetry messages reaching UI endpoint!")
                print("   This means the coaching service is not forwarding telemetry data.")
                print("   Possible causes:")
                print("   1. Coaching service not connected to telemetry service")
                print("   2. Telemetry service not sending data")
                print("   3. Message forwarding logic issue in coaching service")
            else:
                print("\n✅ SUCCESS: Telemetry data is flowing correctly!")
                
    except Exception as e:
        print(f"  ❌ Failed to connect to coaching service: {e}")

if __name__ == "__main__":
    asyncio.run(trace_data_flow())
