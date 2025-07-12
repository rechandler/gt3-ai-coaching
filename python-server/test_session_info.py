#!/usr/bin/env python3
"""
Test to verify that the coaching server now includes session_info in its messages.
This test connects as a coaching client and checks what messages we receive.
"""

import asyncio
import websockets
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_coaching_client():
    """Test connecting to the coaching server and checking for session_info"""
    uri = "ws://localhost:8082"
    
    print("🧪 Testing coaching server session info...")
    print(f"📡 Connecting to {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to coaching server")
            
            # Request message history
            history_request = {"type": "get_history", "count": 5}
            await websocket.send(json.dumps(history_request))
            print(f"📤 Sent history request: {history_request}")
            
            # Listen for messages for 30 seconds
            print("👂 Listening for messages (30 seconds)...")
            
            message_count = 0
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    # Wait for a message with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    message_count += 1
                    
                    try:
                        parsed = json.loads(message)
                        print(f"\n📨 Message #{message_count}:")
                        print(f"   Type: {parsed.get('type', 'unknown')}")
                        
                        # Check if this message includes session_info
                        if 'session_info' in parsed:
                            session_info = parsed['session_info']
                            print(f"   ✅ Has session_info!")
                            print(f"      Track: {session_info.get('track_name', 'N/A')}")
                            print(f"      Car: {session_info.get('car_name', 'N/A')}")
                            print(f"      Session Active: {session_info.get('session_active', 'N/A')}")
                            print(f"      Baseline: {session_info.get('baseline_established', 'N/A')}")
                        else:
                            print("   ❌ No session_info in this message")
                        
                        # Show first few fields of the message
                        if len(str(parsed)) > 200:
                            print(f"   Content: {str(parsed)[:200]}...")
                        else:
                            print(f"   Content: {parsed}")
                            
                    except json.JSONDecodeError:
                        print(f"   Raw message: {message[:100]}...")
                        
                    # Stop after 30 seconds
                    if asyncio.get_event_loop().time() - start_time > 30:
                        print(f"\n⏰ Test completed after 30 seconds")
                        break
                        
                except asyncio.TimeoutError:
                    print("   ⏳ No message received in last 5 seconds...")
                    if asyncio.get_event_loop().time() - start_time > 30:
                        break
                        
    except ConnectionRefusedError:
        print("❌ Could not connect to coaching server. Is it running on port 8082?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print(f"\n📊 Test Summary:")
    print(f"   Total messages received: {message_count}")
    print("\n🎯 Expected Behavior:")
    print("   - Coaching server should include 'session_info' object in coaching messages")
    print("   - session_info should contain track_name, car_name, session_active, baseline_established")
    print("   - Frontend can now use reliable session data instead of inconsistent telemetry")
    
    return True

if __name__ == "__main__":
    print("🧪 Session Info Test for GT3 AI Coaching")
    print("="*50)
    print("This test verifies our fix for inconsistent track/car names.")
    print("Before: Frontend showed changing estimated names from telemetry")
    print("After: Frontend gets reliable session info from coaching server")
    print("="*50)
    
    asyncio.run(test_coaching_client())
