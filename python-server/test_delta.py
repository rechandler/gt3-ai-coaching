#!/usr/bin/env python3
"""
Simple test script to check iRacing delta time availability
"""

import time

try:
    import pyirsdk as irsdk
    print("Using pyirsdk")
except ImportError:
    try:
        import irsdk
        print("Using irsdk")
    except ImportError:
        print("ERROR: No iRacing SDK found. Please install pyirsdk")
        exit(1)

def test_delta_fields():
    """Test what delta fields are available from iRacing"""
    ir = irsdk.IRSDK()
    
    print("Testing iRacing SDK connection...")
    
    # Try to connect
    ir.startup()
    
    if not ir.is_connected:
        print("❌ Not connected to iRacing. Start iRacing and join a session first.")
        return False
    
    print("✅ Connected to iRacing!")
    
    # Test delta fields
    delta_fields = [
        'LapDeltaToBestLap',
        'LapDeltaToOptimalLap', 
        'LapDeltaToSessionBestLap',
        'LapCurrentLapTime',
        'LapBestLapTime',
        'OnPitRoad'
    ]
    
    print("\nTesting delta fields:")
    print("-" * 50)
    
    for field in delta_fields:
        try:
            value = ir[field]
            if value is not None:
                print(f"✅ {field}: {value}")
            else:
                print(f"⚠️  {field}: None (field exists but no data)")
        except KeyError:
            print(f"❌ {field}: Field not found")
        except Exception as e:
            print(f"❌ {field}: Error - {e}")
    
    print("\nMonitoring delta for 10 seconds...")
    print("-" * 50)
    
    for i in range(10):
        try:
            delta_best = ir['LapDeltaToBestLap']
            delta_optimal = ir['LapDeltaToOptimalLap']
            current_time = ir['LapCurrentLapTime']
            on_pit_road = ir['OnPitRoad']
            
            print(f"#{i+1}: Delta to Best: {delta_best}, Delta to Optimal: {delta_optimal}, Current: {current_time}, In Pits: {on_pit_road}")
            
        except Exception as e:
            print(f"#{i+1}: Error reading data - {e}")
        
        time.sleep(1)
    
    ir.shutdown()
    return True

if __name__ == "__main__":
    print("GT3 AI Coaching - Delta Time Test")
    print("=" * 50)
    test_delta_fields()
