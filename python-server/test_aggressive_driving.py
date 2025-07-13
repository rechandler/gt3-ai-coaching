#!/usr/bin/env python3
"""
Test Aggressive Driving Scenarios for LLM Coaching
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_aggressive_scenarios():
    print("🏁 Testing Aggressive Driving Scenarios for LLM Coaching\n")
    
    try:
        from ai_coach_simple import LocalAICoach
        
        # Create fresh coach instance
        coach = LocalAICoach()
        coach.start_session("Watkins Glen", "Porsche 992 GT3 R")
        
        # Fill buffer with driving data
        for i in range(25):
            base_telemetry = {
                'Speed': 70 + i,
                'Throttle': 0.5 + i * 0.01, 
                'Brake': 0.0,
                'SteeringWheelAngle': 0.1,
                'LapDistPct': 0.02 + i * 0.02,
                'timestamp': time.time()
            }
            coach.telemetry_buffer.append(base_telemetry.copy())
        
        print(f"📊 Current Thresholds:")
        print(f"   • Heavy Braking: brake > 0.75 AND speed > 50mph")
        print(f"   • Corner Exit: throttle > 0.55 AND steering > 0.35") 
        print(f"   • Steering Correction: steering > 0.45 AND changes > 0.15")
        print(f"   • Throttle Control: throttle changes > 0.25")
        print(f"   • High Speed: speed > 130mph")
        print(f"   • Cooldown: {coach.llm_cooldown}s")
        
        aggressive_scenarios = [
            {
                "name": "HEAVY Braking (80% brake, 90mph)",
                "data": {
                    'LapDistPct': 0.1,
                    'Brake': 0.8,           # > 0.75 ✓
                    'Speed': 90,            # > 50 ✓
                    'Throttle': 0.0,
                    'SteeringWheelAngle': 0.2
                },
                "should_trigger": True
            },
            {
                "name": "Aggressive Corner Exit (60% throttle, 40° steering)",
                "data": {
                    'LapDistPct': 0.5,
                    'Brake': 0.0,
                    'Speed': 55,
                    'Throttle': 0.6,        # > 0.55 ✓
                    'SteeringWheelAngle': 0.4  # > 0.35 ✓
                },
                "should_trigger": True
            },
            {
                "name": "High Steering Input (50° steering)",
                "data": {
                    'LapDistPct': 0.6,
                    'Brake': 0.0,
                    'Speed': 75,
                    'Throttle': 0.4,
                    'SteeringWheelAngle': 0.5  # > 0.45 ✓
                },
                "should_trigger": True
            },
            {
                "name": "Very High Speed (140mph)",
                "data": {
                    'LapDistPct': 0.3,
                    'Brake': 0.0,
                    'Speed': 140,           # > 130 ✓
                    'Throttle': 0.95,
                    'SteeringWheelAngle': 0.05
                },
                "should_trigger": True
            },
            {
                "name": "Normal Driving (shouldn't trigger)",
                "data": {
                    'LapDistPct': 0.4,
                    'Brake': 0.3,           # < 0.75
                    'Speed': 65,
                    'Throttle': 0.5,        # < 0.55
                    'SteeringWheelAngle': 0.25  # < 0.35
                },
                "should_trigger": False
            }
        ]
        
        print(f"\n🧪 Testing Scenarios:\n")
        
        for i, scenario in enumerate(aggressive_scenarios, 1):
            print(f"   📍 Test {i}: {scenario['name']}")
            expected = "Should trigger" if scenario['should_trigger'] else "Should NOT trigger"
            print(f"      Expected: {expected}")
            
            # Reset cooldown
            coach.last_llm_message = 0
            
            # Test detection
            context = coach._detect_coaching_moments(scenario['data'])
            
            if context:
                print(f"      🎯 Detection: {context}")
                try:
                    messages = coach._generate_llm_coaching(scenario['data'])
                    if messages and messages[0].message:
                        print(f"      🤖 LLM: '{messages[0].message}'")
                        if scenario['should_trigger']:
                            print(f"      ✅ SUCCESS! (Expected to trigger)")
                        else:
                            print(f"      ⚠️  UNEXPECTED! (Should not have triggered)")
                    else:
                        print(f"      ❌ No message generated")
                except Exception as e:
                    print(f"      ❌ Error: {e}")
            else:
                if scenario['should_trigger']:
                    print(f"      ❌ MISSED! (Expected to trigger but didn't)")
                else:
                    print(f"      ✅ CORRECT! (Correctly did not trigger)")
            
            print()  # Empty line between tests
        
        print(f"💡 For iRacing Testing:")
        print(f"   • Drive aggressively: >75% brake pressure")
        print(f"   • Aggressive corner exits: >55% throttle + >35° steering")
        print(f"   • High steering inputs: >45° steering wheel")
        print(f"   • Very high speeds: >130mph")
        print(f"   • Messages will appear with 🤖 icon every 3+ seconds")
        
        print(f"\n📋 If still no messages in iRacing:")
        print(f"   1. Check server logs for 'LLM coaching triggered' messages")
        print(f"   2. Make sure you're driving aggressively enough")
        print(f"   3. Check if data units match (m/s vs mph)")
        print(f"   4. Verify iRacing is connected to telemetry server")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_aggressive_scenarios()
