#!/usr/bin/env python3
"""
Direct OpenAI API Test
"""

import requests
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_openai_api_directly():
    try:
        from llm_config import OPENAI_API_KEY, LLM_MODEL
        
        print("🔍 Testing OpenAI API directly...")
        print(f"   • API Key: {OPENAI_API_KEY[:20]}...{OPENAI_API_KEY[-10:] if len(OPENAI_API_KEY) > 30 else OPENAI_API_KEY}")
        print(f"   • Model: {LLM_MODEL}")
        
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Simple test prompt
        payload = {
            'model': LLM_MODEL,
            'messages': [
                {'role': 'system', 'content': 'You are a racing coach. Be concise.'},
                {'role': 'user', 'content': 'The driver just braked heavily at 150mph going into Turn 1. Give them one brief coaching tip under 20 words.'}
            ],
            'max_tokens': 50,
            'temperature': 0.7
        }
        
        print("\n🚀 Making API call to OpenAI...")
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"   • Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content'].strip()
            print(f"   ✅ Success! OpenAI responded: '{message}'")
            print(f"   • Usage: {result.get('usage', {})}")
            return True
            
        elif response.status_code == 429:
            print("   ❌ Rate Limited (429)")
            try:
                error_data = response.json()
                print(f"   • Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
                print(f"   • Type: {error_data.get('error', {}).get('type', 'Unknown')}")
            except:
                print(f"   • Raw response: {response.text}")
                
        elif response.status_code == 401:
            print("   ❌ Unauthorized (401) - Check your API key")
            try:
                error_data = response.json()
                print(f"   • Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
            except:
                print(f"   • Raw response: {response.text}")
                
        elif response.status_code == 400:
            print("   ❌ Bad Request (400)")
            try:
                error_data = response.json()
                print(f"   • Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
            except:
                print(f"   • Raw response: {response.text}")
        else:
            print(f"   ❌ Unexpected error: {response.status_code}")
            print(f"   • Response: {response.text}")
            
        return False
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_key_format():
    try:
        from llm_config import OPENAI_API_KEY
        
        print("\n🔍 Checking API Key Format...")
        
        if OPENAI_API_KEY == "your-openai-api-key-here":
            print("   ❌ API key not set - still using placeholder")
            return False
            
        if not OPENAI_API_KEY.startswith("sk-"):
            print("   ❌ API key doesn't start with 'sk-'")
            return False
            
        if len(OPENAI_API_KEY) < 40:
            print(f"   ❌ API key too short: {len(OPENAI_API_KEY)} chars (should be ~50+)")
            return False
            
        print(f"   ✅ API key format looks correct: {len(OPENAI_API_KEY)} chars, starts with 'sk-'")
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking API key: {e}")
        return False

if __name__ == "__main__":
    print("🧪 OpenAI API Direct Test\n")
    
    # Test API key format first
    if test_api_key_format():
        # Then test actual API call
        test_openai_api_directly()
    
    print("\n📝 If you're seeing rate limits:")
    print("   • Your API key might have usage limits")
    print("   • Try waiting a few minutes")
    print("   • Check your OpenAI account billing/usage")
    print("   • Consider upgrading your OpenAI plan")
