#!/usr/bin/env python3
"""
Test script for GT3 AI Coach session persistence
"""

import time
import json
from ai_coach_simple import LocalAICoach

def test_local_persistence():
    """Test local session persistence without cloud"""
    print("🧪 Testing Local Session Persistence...")
    
    # Create coach with local persistence only
    coach = LocalAICoach(cloud_sync_enabled=False)
    
    # Start a session
    print("📝 Starting test session...")
    coach.start_session("Test Track", "Test Car", load_previous=False)
    
    # Simulate some telemetry data
    print("🏁 Simulating 5 laps...")
    for lap_num in range(1, 6):
        # Simulate lap completion
        coach.current_lap_data = {
            'lap_number': lap_num,
            'current_lap_time': 85.0 + (lap_num * 0.5),  # Getting slightly faster
            'speed': 120,
            'throttle': 80,
            'brake': 0
        }
        coach._complete_lap()
        
        # Simulate some telemetry during the lap
        test_telemetry = {
            'lap': lap_num,
            'lapCurrentLapTime': 85.0 + (lap_num * 0.5),
            'speed': 120,
            'throttle': 80,
            'brake': 0,
            'playerTrackSurface': 4  # On track
        }
        
        messages = coach.process_telemetry(test_telemetry)
        if messages:
            print(f"   Lap {lap_num}: {messages[0].message}")
    
    # Check session summary
    summary = coach.get_session_summary()
    print("\n📊 Session Summary:")
    print(f"   Laps: {summary['laps_completed']}")
    print(f"   Best: {summary['best_lap_time']:.3f}s")
    print(f"   Baseline: {summary['baseline_established']}")
    
    # Finish session
    coach.finish_session()
    
    # Test loading previous session
    print("\n🔄 Testing session loading...")
    coach2 = LocalAICoach(cloud_sync_enabled=False)
    coach2.start_session("Test Track", "Test Car", load_previous=True)
    
    if coach2.baseline_established:
        print("✅ Successfully loaded previous baseline!")
        print(f"   Style: {coach2.driving_style}")
        print(f"   Consistency: {coach2.consistency_threshold:.1%}")
    else:
        print("❌ Failed to load previous baseline")
    
    # Test getting previous sessions
    previous = coach2.get_previous_sessions(limit=5)
    print(f"\n📜 Found {len(previous)} previous sessions")
    for session in previous:
        print(f"   Session: {session['session_id'][:20]}... - {session['laps_count']} laps")
    
    print("\n✅ Local persistence test completed!")

def test_cloud_setup():
    """Test cloud sync setup (without actually connecting)"""
    print("\n☁️ Testing Cloud Setup...")
    
    coach = LocalAICoach(cloud_sync_enabled=True)
    
    # Test Firebase setup (will fail without credentials, but should not crash)
    try:
        result = coach.persistence_manager.setup_firebase_sync("fake_key.json")
        print(f"Firebase setup result: {result}")
    except Exception as e:
        print(f"Expected Firebase error: {e}")
    
    # Test AWS setup (will fail without credentials)
    try:
        aws_config = {
            'access_key': 'fake_key',
            'secret_key': 'fake_secret',
            'region': 'us-east-1',
            'bucket_name': 'test-bucket'
        }
        result = coach.persistence_manager.setup_aws_sync(aws_config)
        print(f"AWS setup result: {result}")
    except Exception as e:
        print(f"Expected AWS error: {e}")
    
    print("✅ Cloud setup tests completed (errors expected without real credentials)")

def test_baseline_reset():
    """Test baseline reset functionality"""
    print("\n🔄 Testing Baseline Reset...")
    
    coach = LocalAICoach()
    coach.start_session("Reset Test Track", "Reset Test Car", load_previous=False)
    
    # Establish a baseline
    for lap_num in range(1, 4):
        coach.current_lap_data = {
            'lap_number': lap_num,
            'current_lap_time': 90.0,
            'speed': 100,
            'throttle': 70,
            'brake': 0
        }
        coach._complete_lap()
    
    print(f"Baseline established: {coach.baseline_established}")
    
    # Reset baseline
    success = coach.reset_baseline()
    print(f"Reset successful: {success}")
    print(f"Baseline after reset: {coach.baseline_established}")
    
    coach.finish_session()
    print("✅ Baseline reset test completed!")

if __name__ == "__main__":
    print("🚀 GT3 AI Coach Persistence Tests\n")
    
    try:
        test_local_persistence()
        test_baseline_reset()
        test_cloud_setup()
        
        print("\n🎉 All tests completed!")
        print("\n📁 Check the 'coaching_data' folder for saved session files")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
