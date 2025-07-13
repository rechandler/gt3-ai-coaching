#!/usr/bin/env python3
"""
Debug Detection Logic Issues
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_detection():
    print("🔍 Debugging Detection Logic\n")
    
    try:
        from ai_coach_simple import LocalAICoach
        
        coach = LocalAICoach()
        coach.start_session("Watkins Glen", "Porsche 992 GT3 R")
        
        # Fill buffer with baseline data
        for i in range(25):
            base_telemetry = {
                'Speed': 50 + i,
                'Throttle': 0.3,
                'Brake': 0.0,
                'SteeringWheelAngle': 0.1,
                'LapDistPct': 0.5,
                'timestamp': time.time()
            }
            coach.telemetry_buffer.append(base_telemetry.copy())
        
        print("🧪 Testing individual detection cases:\n")
        
        # Test steering angle detection
        steering_test = {
            'Speed': 65,
            'Throttle': 0.3,
            'Brake': 0.0,
            'SteeringWheelAngle': 0.25,  # EXACTLY 25° (0.25 radians)
            'LapDistPct': 0.6
        }
        
        print("📍 Steering Test (25° = 0.25 radians):")
        print(f"   SteeringWheelAngle: {steering_test['SteeringWheelAngle']}")
        print(f"   abs(steering) = {abs(steering_test['SteeringWheelAngle'])}")
        print(f"   Threshold: > 0.25")
        print(f"   Check: {abs(steering_test['SteeringWheelAngle'])} > 0.25 = {abs(steering_test['SteeringWheelAngle']) > 0.25}")
        
        context = coach._detect_coaching_moments(steering_test)
        print(f"   Result: {context}")
        print()
        
        # Test with slightly higher steering
        steering_test2 = steering_test.copy()
        steering_test2['SteeringWheelAngle'] = 0.26  # Just above threshold
        print("📍 Steering Test 2 (26° = 0.26 radians):")
        print(f"   SteeringWheelAngle: {steering_test2['SteeringWheelAngle']}")
        print(f"   Check: {abs(steering_test2['SteeringWheelAngle'])} > 0.25 = {abs(steering_test2['SteeringWheelAngle']) > 0.25}")
        
        context2 = coach._detect_coaching_moments(steering_test2)
        print(f"   Result: {context2}")
        print()
        
        # Test corner exit (throttle AND steering)
        corner_test = {
            'Speed': 55,
            'Throttle': 0.4,  # EXACTLY 40%
            'Brake': 0.0,
            'SteeringWheelAngle': 0.2,  # EXACTLY 20°
            'LapDistPct': 0.5
        }
        
        print("📍 Corner Exit Test (40% throttle + 20° steering):")
        print(f"   Throttle: {corner_test['Throttle']} (check: > 0.4 = {corner_test['Throttle'] > 0.4})")
        print(f"   Steering: {abs(corner_test['SteeringWheelAngle'])} (check: > 0.2 = {abs(corner_test['SteeringWheelAngle']) > 0.2})")
        print(f"   Both conditions: {corner_test['Throttle'] > 0.4 and abs(corner_test['SteeringWheelAngle']) > 0.2}")
        
        context3 = coach._detect_coaching_moments(corner_test)
        print(f"   Result: {context3}")
        print()
        
        # Test with slightly higher values
        corner_test2 = corner_test.copy()
        corner_test2['Throttle'] = 0.41
        corner_test2['SteeringWheelAngle'] = 0.21
        
        print("📍 Corner Exit Test 2 (41% throttle + 21° steering):")
        print(f"   Throttle: {corner_test2['Throttle']} (check: > 0.4 = {corner_test2['Throttle'] > 0.4})")
        print(f"   Steering: {abs(corner_test2['SteeringWheelAngle'])} (check: > 0.2 = {abs(corner_test2['SteeringWheelAngle']) > 0.2})")
        print(f"   Both conditions: {corner_test2['Throttle'] > 0.4 and abs(corner_test2['SteeringWheelAngle']) > 0.2}")
        
        context4 = coach._detect_coaching_moments(corner_test2)
        print(f"   Result: {context4}")
        print()
        
        # Test late braking (30% brake at 65mph)
        late_brake_test = {
            'Speed': 65,  # In MPH  
            'Throttle': 0.0,
            'Brake': 0.3,  # EXACTLY 30%
            'SteeringWheelAngle': 0.1,
            'LapDistPct': 0.2
        }
        
        print("📍 Late Braking Test (30% brake at 65mph):")
        print(f"   Brake: {late_brake_test['Brake']} (check: > 0.3 = {late_brake_test['Brake'] > 0.3})")
        print(f"   Speed: {late_brake_test['Speed']} (check: > 60 = {late_brake_test['Speed'] > 60})")
        print(f"   Both conditions: {late_brake_test['Brake'] > 0.3 and late_brake_test['Speed'] > 60}")
        
        context5 = coach._detect_coaching_moments(late_brake_test)
        print(f"   Result: {context5}")
        print()
        
        # Test with slightly higher values
        late_brake_test2 = late_brake_test.copy()
        late_brake_test2['Brake'] = 0.31
        
        print("📍 Late Braking Test 2 (31% brake at 65mph):")
        print(f"   Brake: {late_brake_test2['Brake']} (check: > 0.3 = {late_brake_test2['Brake'] > 0.3})")
        
        context6 = coach._detect_coaching_moments(late_brake_test2)
        print(f"   Result: {context6}")
        print()
        
        print("🎯 Key Findings:")
        print("   • Thresholds use > (greater than), not >= (greater than or equal)")
        print("   • Values must be ABOVE the threshold, not equal to it")
        print("   • 0.25 steering is NOT > 0.25 (false)")
        print("   • 0.4 throttle is NOT > 0.4 (false)")
        print("   • 0.3 brake is NOT > 0.3 (false)")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_detection()
