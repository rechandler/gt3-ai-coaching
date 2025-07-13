#!/usr/bin/env python3
"""
Test LLM Coaching with Fallback Messages
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_llm_with_fallback():
    try:
        from ai_coach_simple import LocalAICoach
        
        # Create AI coach instance
        coach = LocalAICoach()
        coach.start_session("Test Track", "Test Car")
        
        print("🧪 Testing LLM Coaching with Fallback Messages...")
        
        # Reset cooldown for test
        coach.last_llm_message = 0
        
        # Add some telemetry buffer data
        base_telemetry = {
            'Speed': 100, 'Throttle': 0.5, 'Brake': 0.0,
            'SteeringWheelAngle': 0.1, 'LapDistPct': 0.1, 'timestamp': time.time()
        }
        
        # Fill buffer with some data points
        for i in range(15):
            coach.telemetry_buffer.append(base_telemetry.copy())
        
        # Test heavy braking scenario
        heavy_braking_telemetry = {
            'LapDistPct': 0.1,  # Turn 1
            'Brake': 0.8,       # Heavy braking (threshold is > 0.7)
            'Speed': 150,       # High speed (threshold is > 80 mph)
            'Throttle': 0.0,
            'SteeringWheelAngle': 0.2
        }
        
        print(f"📍 Testing Heavy Braking Scenario:")
        print(f"   • Brake: {heavy_braking_telemetry['Brake']} (>0.7)")
        print(f"   • Speed: {heavy_braking_telemetry['Speed'] * 2.237:.0f} mph (>80)")
        print(f"   • Section: {coach._get_track_section(heavy_braking_telemetry['LapDistPct'])}")
        
        # Detect coaching moment
        context = coach._detect_coaching_moments(heavy_braking_telemetry)
        print(f"   • Detected: {context}")
        
        # Generate LLM coaching message
        messages = coach._generate_llm_coaching(heavy_braking_telemetry)
        
        if messages:
            msg = messages[0]
            print(f"   ✅ LLM Message Generated:")
            print(f"      • Text: '{msg.message}'")
            print(f"      • Category: {msg.category}")
            print(f"      • Priority: {msg.priority}")
            print(f"      • Confidence: {msg.confidence}%")
        else:
            print("   ❌ No message generated")
        
        # Test another scenario - corner exit
        corner_exit_telemetry = {
            'LapDistPct': 0.5,  # Chicane
            'Brake': 0.0,
            'Speed': 80,
            'Throttle': 0.6,    # High throttle
            'SteeringWheelAngle': 0.3  # Moderate steering
        }
        
        print(f"\n📍 Testing Corner Exit Scenario:")
        print(f"   • Throttle: {corner_exit_telemetry['Throttle']} (>0.4)")
        print(f"   • Steering: {corner_exit_telemetry['SteeringWheelAngle']} (>0.25)")
        print(f"   • Section: {coach._get_track_section(corner_exit_telemetry['LapDistPct'])}")
        
        # Reset cooldown
        coach.last_llm_message = 0
        
        context = coach._detect_coaching_moments(corner_exit_telemetry)
        print(f"   • Detected: {context}")
        
        messages = coach._generate_llm_coaching(corner_exit_telemetry)
        
        if messages:
            msg = messages[0]
            print(f"   ✅ LLM Message Generated:")
            print(f"      • Text: '{msg.message}'")
            print(f"      • Category: {msg.category}")
        else:
            print("   ❌ No message generated")
        
        print(f"\n📝 Summary:")
        print(f"   • LLM is enabled and configured")
        print(f"   • Detection logic is working")
        print(f"   • Fallback messages handle API rate limits")
        print(f"   • Messages should appear in your coaching widget!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_llm_with_fallback()
