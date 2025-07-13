#!/usr/bin/env python3
"""
Test LLM Coaching Message Generation
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_llm_message_generation():
    try:
        from ai_coach_simple import LocalAICoach
        
        # Create AI coach instance
        coach = LocalAICoach()
        
        print("🧪 Testing LLM Message Generation...")
        print(f"   • LLM Enabled: {coach.llm_enabled}")
        print(f"   • API Key Length: {len(coach.llm_api_key)} chars")
        print(f"   • Model: {coach.llm_model}")
        
        if not coach.llm_enabled:
            print("❌ LLM is disabled. Enable it in llm_config.py")
            return False
        
        # Simulate telemetry that should trigger LLM coaching
        test_scenarios = [
            {
                "name": "Heavy braking into Turn 1",
                "telemetry": {
                    'LapDistPct': 0.1,  # Turn 1
                    'Brake': 0.9,       # Heavy braking
                    'Speed': 150,       # High speed
                    'Throttle': 0.0,
                    'SteeringWheelAngle': 0.2
                }
            },
            {
                "name": "Throttle control issue at chicane",
                "telemetry": {
                    'LapDistPct': 0.5,  # Chicane
                    'Brake': 0.0,
                    'Speed': 80,
                    'Throttle': 0.7,    # High throttle
                    'SteeringWheelAngle': 0.4
                }
            },
            {
                "name": "Steering correction at fast corners",
                "telemetry": {
                    'LapDistPct': 0.6,  # Fast corners
                    'Brake': 0.0,
                    'Speed': 120,
                    'Throttle': 0.8,
                    'SteeringWheelAngle': 0.6  # Heavy steering
                }
            }
        ]
        
        # Initialize the coach properly
        coach.start_session("Test Track", "Test Car")
        
        # Add some telemetry buffer data to simulate driving
        base_telemetry = {
            'Speed': 100, 'Throttle': 0.5, 'Brake': 0.0,
            'SteeringWheelAngle': 0.1, 'LapDistPct': 0.0, 'timestamp': time.time()
        }
        
        # Fill buffer with 50 data points
        for i in range(50):
            coach.telemetry_buffer.append(base_telemetry.copy())
        
        print("\n🎯 Testing Coaching Moment Detection:")
        
        for scenario in test_scenarios:
            print(f"\n   📍 {scenario['name']}:")
            
            # Test situation detection
            coaching_context = coach._detect_coaching_moments(scenario['telemetry'])
            print(f"      • Detected situation: {coaching_context}")
            
            # Test track section detection
            section = coach._get_track_section(scenario['telemetry'].get('LapDistPct', 0))
            print(f"      • Track section: {section}")
            
            # Try to generate LLM message (but don't actually call API)
            if coaching_context:
                print(f"      • Would generate LLM message for: {coaching_context}")
                print("      • ✅ This scenario should trigger LLM coaching")
            else:
                print("      • ❌ No coaching situation detected")
        
        print("\n🔍 Debugging LLM Integration:")
        print(f"   • LLM cooldown: {coach.llm_cooldown}s")
        print(f"   • Last LLM message time: {coach.last_llm_message}")
        print(f"   • Current time: {time.time()}")
        
        # Test a real LLM call with a simple scenario
        if coach.llm_enabled and coach.llm_api_key != "your-openai-api-key-here":
            print("\n🚀 Testing Real LLM API Call...")
            
            try:
                # Reset cooldown for test
                coach.last_llm_message = 0
                
                # Test with heavy braking scenario
                test_telemetry = {
                    'LapDistPct': 0.1,  # Turn 1
                    'Brake': 0.9,       # Heavy braking
                    'Speed': 150,       # High speed  
                    'Throttle': 0.0,
                    'SteeringWheelAngle': 0.2
                }
                
                # Add recent telemetry for context
                for i in range(30):
                    coach.telemetry_buffer.append(test_telemetry.copy())
                
                messages = coach._generate_llm_coaching(test_telemetry)
                
                if messages:
                    print(f"   ✅ LLM generated message: '{messages[0].text}'")
                    print(f"   • Category: {messages[0].category}")
                    print(f"   • Priority: {messages[0].priority}")
                else:
                    print("   ❌ No LLM message generated")
                    
            except Exception as e:
                print(f"   ❌ LLM API call failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_llm_message_generation()
