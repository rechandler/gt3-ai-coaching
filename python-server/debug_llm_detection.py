#!/usr/bin/env python3
"""
Debug LLM Detection with Realistic iRacing Data
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_realistic_driving():
    print("🔍 Debugging LLM Detection with Realistic iRacing Data\n")
    
    try:
        from ai_coach_simple import LocalAICoach
        
        # Create fresh coach instance
        coach = LocalAICoach()
        coach.start_session("Watkins Glen", "Porsche 992 GT3 R")
        
        print(f"📊 Current Detection Settings:")
        print(f"   • LLM Enabled: {coach.llm_enabled}")
        print(f"   • API Key Set: {coach.llm_api_key != 'your-openai-api-key-here'}")
        print(f"   • Cooldown: {coach.llm_cooldown}s")
        print(f"   • Buffer Size: {len(coach.telemetry_buffer)}")
        
        # Add base telemetry to fill buffer (simulate driving)
        print(f"\n🏁 Simulating Normal Driving...")
        for i in range(20):
            base_telemetry = {
                'Speed': 80 + i * 2,  # Gradually increasing speed
                'Throttle': 0.6 + i * 0.01, 
                'Brake': 0.0,
                'SteeringWheelAngle': 0.1 + (i % 3) * 0.05,
                'LapDistPct': 0.05 + i * 0.02,
                'timestamp': time.time()
            }
            coach.telemetry_buffer.append(base_telemetry.copy())
        
        print(f"   • Buffer filled with {len(coach.telemetry_buffer)} data points")
        
        # Test realistic scenarios with iRacing data ranges
        scenarios = [
            {
                "name": "Moderate Braking into T1 (70% brake, 85mph)",
                "data": {
                    'LapDistPct': 0.1,      # Turn 1
                    'Brake': 0.7,           # 70% brake (was 0.8)
                    'Speed': 85,            # 85 mph (was 150)
                    'Throttle': 0.0,
                    'SteeringWheelAngle': 0.15
                },
                "expected": "Should trigger: brake > 0.7 and speed > 80mph"
            },
            {
                "name": "Light Braking (50% brake, 90mph)",
                "data": {
                    'LapDistPct': 0.2,
                    'Brake': 0.5,           # 50% brake
                    'Speed': 90,            # 90 mph
                    'Throttle': 0.0,
                    'SteeringWheelAngle': 0.2
                },
                "expected": "Should NOT trigger: brake < 0.7"
            },
            {
                "name": "Corner Exit with Throttle (60% throttle, 45° steering)",
                "data": {
                    'LapDistPct': 0.5,      # Chicane
                    'Brake': 0.0,
                    'Speed': 65,
                    'Throttle': 0.6,        # 60% throttle (was 0.6)
                    'SteeringWheelAngle': 0.45  # 45° steering (was 0.3)
                },
                "expected": "Should trigger: throttle > 0.4 and steering > 0.25"
            },
            {
                "name": "High Speed Straight (120mph, minimal inputs)",
                "data": {
                    'LapDistPct': 0.3,      # Back straight
                    'Brake': 0.0,
                    'Speed': 120,           # 120 mph
                    'Throttle': 0.95,
                    'SteeringWheelAngle': 0.05
                },
                "expected": "Should trigger: speed > 100mph"
            },
            {
                "name": "Normal Corner (50mph, 30° steering)",
                "data": {
                    'LapDistPct': 0.7,
                    'Brake': 0.0,
                    'Speed': 50,
                    'Throttle': 0.3,
                    'SteeringWheelAngle': 0.3   # 30° steering
                },
                "expected": "Should NOT trigger: speed < 100, throttle < 0.4"
            }
        ]
        
        print(f"\n🧪 Testing Realistic Scenarios:")
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n   📍 Test {i}: {scenario['name']}")
            print(f"      Expected: {scenario['expected']}")
            
            # Reset cooldown for each test
            coach.last_llm_message = 0
            
            # Test detection
            context = coach._detect_coaching_moments(scenario['data'])
            print(f"      🎯 Detection Result: {context}")
            
            if context:
                # Try to generate message
                try:
                    messages = coach._generate_llm_coaching(scenario['data'])
                    if messages and messages[0].message:
                        print(f"      🤖 LLM Message: '{messages[0].message}'")
                        print(f"      ✅ SUCCESS!")
                    else:
                        print(f"      ❌ No message generated (cooldown or API issue)")
                except Exception as e:
                    print(f"      ❌ Error generating message: {e}")
            else:
                print(f"      ❌ No coaching situation detected")
        
        print(f"\n🔧 Detection Logic Analysis:")
        print(f"   Heavy Braking: brake > 0.7 AND speed > 80mph")
        print(f"   Corner Exit: throttle > 0.4 AND steering > 0.25")  
        print(f"   High Speed: speed > 100mph")
        print(f"   Steering Correction: steering > 0.4 AND recent steering changes > 0.15")
        print(f"   Throttle Control: throttle changes > 0.25")
        
        print(f"\n💡 Possible Issues:")
        print(f"   1. ⚡ Detection thresholds too high for your driving style")
        print(f"   2. 📊 iRacing data format different than expected") 
        print(f"   3. ⏱️ Cooldown preventing messages (5s between messages)")
        print(f"   4. 🔄 Buffer not filled during normal driving")
        print(f"   5. 📡 Data not reaching detection logic")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_realistic_driving()
