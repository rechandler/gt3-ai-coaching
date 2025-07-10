#!/usr/bin/env python3
"""
Quick iRacing connection test
"""

try:
    import pyirsdk as irsdk
    SDK_TYPE = "pyirsdk"
    print("Using pyirsdk")
except ImportError:
    try:
        import irsdk
        SDK_TYPE = "irsdk"
        print("Using irsdk")
    except ImportError:
        print("ERROR: No iRacing SDK found")
        exit(1)

def test_connection():
    ir = irsdk.IRSDK()
    
    print(f"\n🔍 Testing iRacing connection...")
    print(f"SDK Type: {SDK_TYPE}")
    
    # Check available methods
    methods = ['startup', 'shutdown', 'is_initialized', 'is_connected']
    for method in methods:
        if hasattr(ir, method):
            attr = getattr(ir, method)
            print(f"✅ {method}: {type(attr)} - {'callable' if callable(attr) else 'property'}")
        else:
            print(f"❌ {method}: Not available")
    
    # Try startup
    print(f"\n🚀 Attempting startup...")
    try:
        if hasattr(ir, 'startup'):
            result = ir.startup()
            print(f"Startup result: {result}")
        else:
            print("No startup method available")
    except Exception as e:
        print(f"Startup error: {e}")
    
    # Check connection status
    print(f"\n📡 Checking connection...")
    try:
        if hasattr(ir, 'is_connected'):
            connected = ir.is_connected
            print(f"is_connected: {connected}")
        else:
            print("No is_connected property")
            
        if hasattr(ir, 'is_initialized'):
            initialized = ir.is_initialized
            print(f"is_initialized: {initialized}")
        else:
            print("No is_initialized property")
    except Exception as e:
        print(f"Connection check error: {e}")
    
    # Try to get some telemetry
    print(f"\n📊 Testing telemetry access...")
    test_fields = ['SessionTime', 'Speed', 'RPM', 'Lap']
    for field in test_fields:
        try:
            value = ir[field]
            print(f"✅ {field}: {value}")
        except Exception as e:
            print(f"❌ {field}: {e}")
    
    # Test session info
    print(f"\n📋 Testing session info...")
    try:
        if hasattr(ir, 'session_info'):
            session_info = ir.session_info
            if session_info:
                print(f"✅ session_info: {type(session_info)} - {len(str(session_info))} chars")
            else:
                print("❌ session_info: None")
        else:
            print("❌ No session_info property")
    except Exception as e:
        print(f"❌ Session info error: {e}")

if __name__ == "__main__":
    test_connection()
