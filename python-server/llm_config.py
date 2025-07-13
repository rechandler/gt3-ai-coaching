# LLM Configuration for AI Coaching
# 
# To enable LLM coaching, follow these steps:
#
# 1. Get an OpenAI API key from https://platform.openai.com/api-keys
# 2. Set your API key in the OPENAI_API_KEY variable below
# 3. Set LLM_ENABLED to True
# 4. Restart the coaching server

# LLM Settings
LLM_ENABLED = True  # Set to True to enable LLM coaching
OPENAI_API_KEY = "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"  # Replace with your actual API key
LLM_MODEL = "gpt-3.5-turbo"  # Can also use "gpt-4" for better quality
LLM_COOLDOWN = 2.0  # Seconds between LLM messages

# Track section names (can be customized for specific tracks)
TRACK_SECTIONS = {
    0.0: "Start/Finish Straight",
    0.1: "Turn 1", 
    0.2: "First Complex",
    0.3: "Back Straight",
    0.4: "Turn 2",
    0.5: "Chicane", 
    0.6: "Fast Corners",
    0.7: "Tight Corners",
    0.8: "Final Sector",
    0.9: "Last Corner"
}

# Example messages the LLM will generate:
# - "Brake earlier going into Turn 1"
# - "You accelerated too hard coming out of that corner" 
# - "Ease off the throttle through the chicane"
# - "Try a later braking point there"
# - "Smooth out your steering in the fast corners"
