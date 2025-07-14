"""
Port Architecture Verification Tool
Checks that all services are running on correct ports and can communicate
"""
import asyncio
import json
import websockets
import socket
from contextlib import closing

def check_port(host, port):
    """Check if a port is open and listening"""
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except:
        return False

async def check_websocket_connection(uri, service_name):
    """Check if a WebSocket service is responding"""
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ {service_name} at {uri} - Connected")
            return True
    except Exception as e:
        print(f"❌ {service_name} at {uri} - Failed: {e}")
        return False

async def verify_architecture():
    """Verify the complete port architecture"""
    print("🔍 GT3 AI Coaching - Port Architecture Verification")
    print("=" * 60)
    
    # Check if ports are listening
    print("\n📡 Port Availability Check:")
    ports_to_check = [
        (9001, "Telemetry Service - Telemetry Stream"),
        (9002, "Telemetry Service - Session Stream"), 
        (8082, "Coaching Service - UI Interface")
    ]
    
    all_ports_open = True
    for port, description in ports_to_check:
        is_open = check_port("localhost", port)
        status = "✅ LISTENING" if is_open else "❌ NOT AVAILABLE"
        print(f"  Port {port}: {status} - {description}")
        if not is_open:
            all_ports_open = False
    
    if not all_ports_open:
        print("\n⚠️  Some services are not running. Please start them in order:")
        print("  1. python services/telemetry_service.py")
        print("  2. python services/coaching_data_service.py")
        return
    
    # Check WebSocket connectivity  
    print("\n🔌 WebSocket Connectivity Check:")
    
    # Test telemetry service endpoints
    telemetry_ok = await check_websocket_connection(
        "ws://localhost:9001", "Telemetry Stream"
    )
    session_ok = await check_websocket_connection(
        "ws://localhost:9002", "Session Stream"
    )
    coaching_ok = await check_websocket_connection(
        "ws://localhost:8082", "Coaching Service"
    )
    
    print("\n📊 Architecture Verification:")
    if telemetry_ok and session_ok and coaching_ok:
        print("✅ All services are running correctly!")
        print("\n🏗️  Current Architecture:")
        print("  React UI (Browser) ──────▶ Port 8082 (Coaching Service)")
        print("                                    │")
        print("                                    ├─▶ Port 9001 (Telemetry)")
        print("                                    └─▶ Port 9002 (Session)")
        print("                                           │")
        print("                                    Telemetry Service")
        print("                                           │")
        print("                                      iRacing SDK")
        
        # Test data flow
        print("\n📈 Testing Data Flow:")
        try:
            async with websockets.connect("ws://localhost:8082") as ws:
                print("✅ UI can connect to Coaching Service")
                
                # Wait for a message
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(message)
                    print(f"✅ Receiving data: {data.get('type', 'unknown')} message")
                except asyncio.TimeoutError:
                    print("⚠️  No immediate data (this might be normal)")
                    
        except Exception as e:
            print(f"❌ Data flow test failed: {e}")
            
    else:
        print("❌ Some services failed connectivity test")
        print("\n🔧 Troubleshooting:")
        if not telemetry_ok or not session_ok:
            print("  - Check telemetry service: python services/telemetry_service.py")
        if not coaching_ok:
            print("  - Check coaching service: python services/coaching_data_service.py")

if __name__ == "__main__":
    asyncio.run(verify_architecture())
