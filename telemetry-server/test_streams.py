"""
Quick test client to verify telemetry data streaming
"""
import asyncio
import json
import websockets

async def test_telemetry_stream():
    """Test connection to telemetry stream"""
    try:
        uri = "ws://localhost:9001"
        async with websockets.connect(uri) as websocket:
            print("📊 Connected to telemetry stream")
            
            # Receive a few messages
            for i in range(5):
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "telemetry":
                    telemetry = data.get("data", {})
                    print(f"🚗 Telemetry {i+1}: Speed={telemetry.get('speed', 0):.1f} mph, "
                          f"RPM={telemetry.get('rpm', 0):.0f}, "
                          f"Gear={telemetry.get('gear', 0)}, "
                          f"Throttle={telemetry.get('throttle', 0):.1f}%")
                else:
                    print(f"📋 Message {i+1}: {data.get('type', 'unknown')}")
                    
    except Exception as e:
        print(f"❌ Telemetry stream error: {e}")

async def test_session_stream():
    """Test connection to session stream"""
    try:
        uri = "ws://localhost:9002"
        async with websockets.connect(uri) as websocket:
            print("🏁 Connected to session stream")
            
            # Receive a few messages
            for i in range(3):
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "session":
                    session = data.get("data", {})
                    print(f"🏁 Session {i+1}: Track='{session.get('trackName', 'Unknown')}', "
                          f"Car='{session.get('carName', 'Unknown')}'")
                else:
                    print(f"📋 Session message {i+1}: {data.get('type', 'unknown')}")
                    
    except Exception as e:
        print(f"❌ Session stream error: {e}")

async def test_ui_stream():
    """Test connection to UI stream"""
    try:
        uri = "ws://localhost:8082"
        async with websockets.connect(uri) as websocket:
            print("🖥️ Connected to UI stream")
            
            # Receive a few messages
            for i in range(5):
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "telemetry":
                    telemetry = data.get("data", {})
                    print(f"🖥️ UI Telemetry {i+1}: Speed={telemetry.get('speed', 0):.1f} mph, "
                          f"Intensity={telemetry.get('drivingIntensity', 0):.1f}%, "
                          f"Engine Stress={telemetry.get('engineStress', 0):.1f}%")
                elif data.get("type") == "sessionInfo":
                    session = data.get("data", {})
                    print(f"🖥️ UI Session {i+1}: Track='{session.get('trackName', 'Unknown')}', "
                          f"Car='{session.get('carName', 'Unknown')}'")
                else:
                    print(f"📋 UI message {i+1}: {data.get('type', 'unknown')}")
                    
    except Exception as e:
        print(f"❌ UI stream error: {e}")

async def main():
    print("🔍 Testing GT3 AI Coaching Telemetry Streams")
    print("=" * 50)
    
    # Test all streams concurrently
    await asyncio.gather(
        test_telemetry_stream(),
        test_session_stream(), 
        test_ui_stream()
    )

if __name__ == "__main__":
    asyncio.run(main())
