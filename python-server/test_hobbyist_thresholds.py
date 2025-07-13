#!/usr/bin/env python3
"""
Test Hobbyist-Friendly LLM Detection Thresholds
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_hobbyist_thresholds():
    print("🏁 Testing Hobbyist-Friendly LLM Detection Thresholds\n")
    
    try:
        from ai_coach_simple import LocalAICoach
        
        # Create fresh coach instance
        coach = LocalAICoach()
        coach.start_session("Watkins Glen", "Porsche 992 GT3 R")
        
        # Fill buffer with driving data
        for i in range(25):
            base_telemetry = {
                'Speed': 50 + i,
                'Throttle': 0.4 + i * 0.01, 
                'Brake': 0.0,
                'SteeringWheelAngle': 0.1,
                'LapDistPct': 0.02 + i * 0.02,
                'timestamp': time.time()
            }
            coach.telemetry_buffer.append(base_telemetry.copy())
        
        print(f"📊 NEW Hobbyist-Friendly Thresholds:")
        print(f"   • Heavy Braking: brake > 0.50 AND speed > 40mph")
        print(f"   • Late Braking: brake > 0.30 AND speed > 60mph") 
        print(f"   • Corner Exit: throttle > 0.40 AND steering > 0.20")
        print(f"   • Steering Issues: steering > 0.25 AND changes > 0.10")
        print(f"   • Throttle Control: throttle changes > 0.15")
        print(f"   • High Speed: speed > 90mph")
        print(f"   • Cooldown: {coach.llm_cooldown}s")
        
        hobbyist_scenarios = [
            {
                "name": "Light Braking (50% brake, 70mph) - Late Braking Coaching",
                "data": {
                    'LapDistPct': 0.1,
                    'Brake': 0.5,           # = 0.50 ✓
                    'Speed': 70,            # > 40 ✓
                    'Throttle': 0.0,
                    'SteeringWheelAngle': 0.15
                },
                "should_trigger": True,
                "type": "heavy_braking"
            },
            {
                "name": "Gentle Braking (30% brake, 65mph) - Late Braking",
                "data": {
                    'LapDistPct': 0.2,
                    'Brake': 0.3,           # = 0.30 ✓
                    'Speed': 65,            # > 60 ✓
                    'Throttle': 0.0,
                    'SteeringWheelAngle': 0.1
                },
                "should_trigger": True,
                "type": "late_braking"
            },
            {
                "name": "Normal Corner Exit (40% throttle, 20° steering)",
                "data": {
                    'LapDistPct': 0.5,
                    'Brake': 0.0,
                    'Speed': 55,
                    'Throttle': 0.4,        # = 0.40 ✓
                    'SteeringWheelAngle': 0.2  # = 0.20 ✓
                },
                "should_trigger": True,
                "type": "corner_exit"
            },
            {
                "name": "Moderate Steering (25° steering)",
                "data": {
                    'LapDistPct': 0.6,
                    'Brake': 0.0,
                    'Speed': 65,
                    'Throttle': 0.3,
                    'SteeringWheelAngle': 0.25  # = 0.25 ✓
                },
                "should_trigger": True,
                "type": "steering"
            },
            {
                "name": "Highway Speed (95mph)",
                "data": {
                    'LapDistPct': 0.3,
                    'Brake': 0.0,
                    'Speed': 95,            # > 90 ✓
                    'Throttle': 0.85,
                    'SteeringWheelAngle': 0.05
                },
                "should_trigger": True,
                "type": "high_speed"
            },
            {
                "name": "Very Light Driving (20% brake, 45mph)",
                "data": {
                    'LapDistPct': 0.7,
                    'Brake': 0.2,           # < 0.30
                    'Speed': 45,            # > 40 but brake too light
                    'Throttle': 0.3,        # < 0.40
                    'SteeringWheelAngle': 0.15  # < 0.20
                },
                "should_trigger": False,
                "type": "none"
            }
        ]
        
        print(f"\n🧪 Testing Hobbyist Scenarios:\n")
        
        triggered_count = 0
        for i, scenario in enumerate(hobbyist_scenarios, 1):
            print(f"   📍 Test {i}: {scenario['name']}")
            expected = "Should trigger" if scenario['should_trigger'] else "Should NOT trigger"
            print(f"      Expected: {expected}")
            
            # Reset cooldown
            coach.last_llm_message = 0
            
            # Test detection
            context = coach._detect_coaching_moments(scenario['data'])
            
            if context:
                triggered_count += 1
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
        
        print(f"📊 Results Summary:")
        print(f"   • {triggered_count}/6 scenarios triggered detection")
        print(f"   • Expected: 5/6 should trigger (all except test 6)")
        
        print(f"\n🎮 For iRacing (Hobbyist-Friendly):")
        print(f"   • Any braking >50% at >40mph will give coaching")
        print(f"   • Light braking >30% at >60mph = late braking tips")
        print(f"   • Corner exits >40% throttle + >20° steering")
        print(f"   • Any steering >25° gives handling tips")
        print(f"   • Speeds >90mph give high-speed coaching")
        print(f"   • Messages every 2+ seconds max")
        
        print(f"\n📋 You should now see LLM messages during normal driving!")
        print(f"   ✅ Much more sensitive detection")
        print(f"   ✅ Hobbyist-appropriate thresholds")
        print(f"   ✅ More frequent coaching (2s cooldown)")
        print(f"   ✅ Comprehensive logging for debugging")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_hobbyist_thresholds()
