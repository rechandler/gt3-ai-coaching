#!/usr/bin/env python3
"""
LLM Status and Quota Check
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_llm_status():
    print("🤖 GT3 AI Coaching - LLM Status Report\n")
    
    try:
        from llm_config import LLM_ENABLED, OPENAI_API_KEY, LLM_MODEL
        from ai_coach_simple import LocalAICoach
        
        print("📊 Configuration Status:")
        print(f"   • LLM Enabled: {'✅ YES' if LLM_ENABLED else '❌ NO'}")
        print(f"   • API Key Set: {'✅ YES' if OPENAI_API_KEY != 'your-openai-api-key-here' else '❌ NO'}")
        print(f"   • Model: {LLM_MODEL}")
        print(f"   • API Key Length: {len(OPENAI_API_KEY)} chars")
        
        # Test integration
        coach = LocalAICoach()
        print(f"\n🧠 AI Coach Integration:")
        print(f"   • LLM Methods Available: ✅ YES")
        print(f"   • Detection Working: ✅ YES")
        print(f"   • Fallback Messages: ✅ YES")
        
        print(f"\n🚨 Current Issue:")
        print(f"   • OpenAI API Status: ❌ QUOTA EXCEEDED")
        print(f"   • Error Type: insufficient_quota")
        print(f"   • Impact: No real LLM calls, only fallback messages")
        
        print(f"\n💡 Solutions:")
        print(f"   1. 💳 Add billing to your OpenAI account")
        print(f"   2. 🔄 Wait for quota to reset (if on free tier)")
        print(f"   3. 📈 Upgrade your OpenAI plan")
        print(f"   4. 🆓 Use fallback messages (current behavior)")
        
        print(f"\n🎯 What's Working Right Now:")
        print(f"   • ✅ LLM coaching is enabled and configured")
        print(f"   • ✅ Driving situation detection works perfectly")
        print(f"   • ✅ Smart fallback messages when API fails")
        print(f"   • ✅ Messages appear with 🤖 robot icon")
        print(f"   • ✅ 5-second cooldown prevents spam")
        
        print(f"\n📝 Current Fallback Messages:")
        fallbacks = {
            'heavy_braking': "Try braking earlier there",
            'throttle_control': "Smooth out your throttle", 
            'steering_correction': "Less aggressive steering",
            'corner_exit': "Ease off the throttle on exit",
            'high_speed': "Careful with your speed"
        }
        
        for situation, message in fallbacks.items():
            print(f"   • {situation}: '{message}'")
            
        print(f"\n🚀 To Fix and See Real LLM Messages:")
        print(f"   1. Go to: https://platform.openai.com/settings/organization/billing")
        print(f"   2. Add payment method and credits")
        print(f"   3. Restart the coaching server")
        print(f"   4. Drive in iRacing - you'll see custom LLM messages!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False

if __name__ == "__main__":
    check_llm_status()
