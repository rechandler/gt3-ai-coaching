#!/usr/bin/env python3
"""
Test LLM Integration for AI Coaching
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_llm_integration():
    try:
        from ai_coach_simple import LocalAICoach
        
        # Create AI coach instance
        coach = LocalAICoach()
        
        print("✅ LLM Integration Test Results:")
        print(f"   • LLM Enabled: {coach.llm_enabled}")
        print(f"   • LLM Model: {coach.llm_model}")
        print(f"   • LLM Cooldown: {coach.llm_cooldown}s")
        print(f"   • API Key Set: {'Yes' if coach.llm_api_key != 'your-openai-api-key-here' else 'No (use llm_config.py)'}")
        print(f"   • Track Sections: {len(coach.track_sections)} defined")
        
        # Test LLM method existence
        llm_methods = [
            '_generate_llm_coaching',
            '_detect_coaching_moments', 
            '_get_track_section',
            '_call_openai_llm'
        ]
        
        print("\n✅ LLM Methods Available:")
        for method in llm_methods:
            if hasattr(coach, method):
                print(f"   • {method}: ✅")
            else:
                print(f"   • {method}: ❌")
        
        print("\n🤖 Example LLM Messages:")
        print("   • 'Brake earlier going into Turn 1'")
        print("   • 'You accelerated too hard coming out of that corner'")
        print("   • 'Ease off the throttle through the chicane'")
        print("   • 'Try a later braking point there'")
        
        print("\n📝 To Enable LLM Coaching:")
        print("   1. Edit llm_config.py")
        print("   2. Set LLM_ENABLED = True")
        print("   3. Add your OpenAI API key")
        print("   4. Restart the server")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM Integration Test Failed: {e}")
        return False

if __name__ == "__main__":
    test_llm_integration()
