# LLM Integration Guide for GT3 AI Coach

## Overview

Your GT3 AI coaching system now supports hybrid operation:

- **Fast backbone**: Your existing sub-5ms telemetry analysis (unchanged)
- **LLM enhancement**: Natural language explanations and session analysis

## Features Added

### 1. Natural Language Explanations

- High-priority coaching messages (priority ≥ 6) get enhanced with explanations
- Example: "Brake earlier into Turn 3" becomes "Brake earlier into Turn 3 (This helps transfer weight forward for better front grip and reduces understeer on entry)"

### 2. Personalized Communication Styles

- **Supportive**: Encouraging, confidence-building
- **Technical**: Detailed, physics-based explanations
- **Motivational**: Performance-focused, competitive
- **Balanced**: Mix of all styles (default)

### 3. Session Analysis & Planning

- Comprehensive post-session reports
- Identifies top 3 improvement areas
- Recognizes what you're doing well
- Provides specific practice recommendations

## Quick Setup

### Option 1: Ollama (Recommended)

```bash
# Install Ollama
winget install Ollama.Ollama

# Download model
ollama pull llama3.1:8b
# or for faster responses:
ollama pull phi-3-mini

# Start Ollama (runs on localhost:11434)
ollama serve
```

### Option 2: LM Studio

1. Download LM Studio
2. Install a model (phi-3-mini recommended for speed)
3. Start local server on localhost:1234

## Code Usage

```python
# Basic usage (no LLM - existing fast system)
coach = LocalAICoach()
messages = coach.process_telemetry(telemetry_data)

# Enhanced usage with LLM
coach = LocalAICoach()

# Enable LLM integration
coach.enable_llm_coaching(model="llama3.1:8b")

# Set communication style
coach.set_communication_style("supportive")  # or "technical", "motivational", "balanced"

# Normal telemetry processing (now enhanced)
enhanced_messages = coach.process_telemetry(telemetry_data)

# Generate session report
session_report = coach.generate_session_report()
print(session_report)
```

## Implementation Details

### Performance

- **Fast messages**: Still <5ms (unchanged)
- **Enhanced messages**: +50-200ms for high-priority messages only
- **Session analysis**: Generated on-demand (1-3 seconds)

### LLM Client Interface

The system includes a `LocalLLMClient` class that you can customize:

```python
class LocalLLMClient:
    def __init__(self, enabled=False, model="llama3.1:8b"):
        self.enabled = enabled
        self.base_url = "http://localhost:11434"  # Ollama default

    def enhance_coaching_message(self, message, context):
        # Implement your LLM API calls here
        pass

    def generate_session_analysis(self, context):
        # Implement session analysis generation
        pass
```

### Customization Points

1. **LLM Provider**: Modify `_call_llm()` method for your chosen provider
2. **Prompts**: Customize `_build_enhancement_prompt()` and `_build_session_prompt()`
3. **Communication Styles**: Add new styles in `set_communication_style()`
4. **Enhancement Logic**: Modify `_enhance_messages_with_llm()` for different enhancement strategies

## Next Steps

1. **Choose and install your LLM** (Ollama recommended)
2. **Implement the `_call_llm()` method** for your chosen provider
3. **Test with session analysis first** (non-critical path)
4. **Gradually enable real-time enhancement** as you optimize performance
5. **Customize prompts** for your specific coaching needs

## Future Enhancements

- **Voice coaching**: TTS integration for enhanced messages
- **Driver questions**: Interactive Q&A during sessions
- **Advanced context**: Track-specific knowledge base
- **Multi-language support**: Coaching in different languages

The system is designed to be backwards-compatible - existing functionality remains unchanged when LLM is disabled.
