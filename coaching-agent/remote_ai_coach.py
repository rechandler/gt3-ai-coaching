#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remote AI Coach
Handles sophisticated coaching using OpenAI API for natural language coaching
"""

import asyncio
import aiohttp
import time
import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import deque
import base64

# Import the new RichContextBuilder
from rich_context_builder import RichContextBuilder, EventContext

logger = logging.getLogger(__name__)

@dataclass
class AICoachingRequest:
    """Request for AI coaching"""
    insight: Dict[str, Any]
    telemetry_data: Dict[str, Any]
    context: Any  # CoachingContext
    rich_context: Optional[EventContext] = None  # New rich context field
    timestamp: float = 0.0

class RateLimiter:
    """Rate limiter for API requests"""
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    def can_make_request(self) -> bool:
        """Check if we can make a request"""
        current_time = time.time()
        
        # Remove old requests
        while self.requests and current_time - self.requests[0] > self.time_window:
            self.requests.popleft()
        
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        """Record a request"""
        self.requests.append(time.time())

class PromptBuilder:
    """Builds prompts for the AI based on context and situation, using detailed segment data and rich context."""
    
    def __init__(self):
        self.base_prompt = """You are an expert {category} racing coach providing real-time, segment-specific coaching advice.\nYou have access to detailed telemetry and track segment data.\n\nKey principles:\n- Be concise and clear (1-2 sentences max)\n- Focus on the most important improvement\n- Use racing terminology appropriately\n- Be encouraging but direct\n- Provide specific numeric feedback when relevant\n\nCurrent session context:\nTrack: {track_name}\nCar: {car_name}\nCategory: {category}\nSession Type: {session_type}\nCoaching Mode: {coaching_mode}\n"""
        
        # Initialize rich context builder
        self.rich_context_builder = RichContextBuilder()

    def format_segment_info(self, segment: dict) -> str:
        if not segment:
            return ""
        seg_name = segment.get('name', 'Unknown')
        seg_type = segment.get('type', 'Unknown')
        seg_desc = segment.get('description', '')
        seg_start = segment.get('start_pct', None)
        seg_end = segment.get('end_pct', None)
        info = f"\nCurrent segment: {seg_name} ({seg_type})"
        if seg_start is not None and seg_end is not None:
            info += f" (lap %: {seg_start:.2f}-{seg_end:.2f})"
        if seg_desc:
            info += f"\nDescription: {seg_desc}"
        info += ("\nProvide coaching advice specific to this segment, using its name and characteristics. "
                 "Always refer to this segment by its name (e.g., 'Pouhon', 'Turn 4', 'Variante Ascari'), not just 'the corner'.")
        return info

    def build_prompt(self, insight: Dict[str, Any], telemetry_data: Dict[str, Any], 
                    context: Any, current_segment: Any = None, rich_context: Optional[EventContext] = None,
                    ml_analysis: Optional[Dict[str, Any]] = None) -> str:
        """Build a prompt for the AI, including detailed segment info, rich context, and ML analysis if available"""
        situation = insight.get('situation', 'general')
        data = insight.get('data', {})
        
        # Add telemetry to rich context builder
        self.rich_context_builder.add_telemetry(telemetry_data)
        
        # Build rich context if not provided
        if rich_context is None:
            event_type = self._determine_event_type(situation, data)
            rich_context = self.rich_context_builder.build_rich_context(
                event_type=event_type,
                telemetry_data=telemetry_data,
                context=context,
                current_segment=current_segment
            )
        
        prompt = self.base_prompt.format(
            track_name=getattr(context, 'track_name', 'Unknown'),
            car_name=getattr(context, 'car_name', 'Unknown'),
            category=getattr(context, 'category', 'Unknown'),
            session_type=getattr(context, 'session_type', 'Practice'),
            coaching_mode=getattr(context, 'coaching_mode', 'Intermediate')
        )
        
        # Add rich context if available
        if rich_context:
            prompt += "\n" + self.rich_context_builder.format_for_prompt(rich_context)
        
        # Add ML analysis if available
        if ml_analysis:
            prompt += "\nML Model Analysis (sub-advisor):\n" + json.dumps(ml_analysis, indent=2)
        
        # Add segment info if available
        if current_segment:
            prompt += self.format_segment_info(current_segment)
        
        # Add subjective driver issue if available
        driver_issue = data.get('driver_issue')
        if driver_issue:
            prompt += f"\nDriver's Issue: {driver_issue}\n"
        
        # Add situation
        prompt += f"\nCurrent situation: {situation}\n"
        confidence = insight.get('confidence', 0.5)
        prompt += f"Confidence level: {confidence:.1%}\n"
        
        # Add telemetry context (simplified since we have rich context)
        if telemetry_data and not rich_context:
            prompt += "\nCurrent telemetry:\n"
            relevant_keys = ['speed', 'brake_pct', 'throttle_pct', 'steering_angle', 
                           'lap_distance_pct', 'gear', 'rpm']
            for key in relevant_keys:
                if key in telemetry_data:
                    prompt += f"- {key}: {telemetry_data[key]}\n"
        
        # Add specific situation data
        if data:
            prompt += f"\nSituation details: {json.dumps(data, indent=2)}\n"
        
        # Add request for specific coaching, tailored to segment type
        prompt += self.get_segment_type_request(current_segment, situation, data)
        
        # Always end with explicit advice request
        prompt += "\nWhat specific advice would you give to address this issue in this segment of the track?"
        
        return prompt
    
    def _determine_event_type(self, situation: str, data: Dict[str, Any]) -> str:
        """Determine event type from situation and data"""
        # Map situations to event types
        situation_to_event = {
            'insufficient_braking': 'late_braking',
            'early_throttle_in_corners': 'early_throttle',
            'inconsistent_lap_times': 'inconsistency',
            'sector_analysis': 'sector_time_loss',
            'corner_analysis': 'corner_technique',
            'race_strategy': 'strategy',
            'understeer': 'understeer',
            'oversteer': 'oversteer',
            'offtrack': 'offtrack',
            'bad_exit': 'bad_exit',
            'missed_apex': 'missed_apex'
        }
        
        # Check for specific patterns in data
        if 'pattern' in data:
            pattern = data['pattern'].lower()
            if 'understeer' in pattern:
                return 'understeer'
            elif 'oversteer' in pattern:
                return 'oversteer'
            elif 'offtrack' in pattern:
                return 'offtrack'
        
        return situation_to_event.get(situation, 'general_technique')

    def get_segment_type_request(self, segment: dict, situation: str, data: Dict[str, Any]) -> str:
        """Get a coaching request tailored to the segment type and situation."""
        seg_type = (segment or {}).get('type', '').lower() if segment else ''
        if seg_type == 'corner':
            return "\nFocus on braking, turn-in, apex, and exit technique for this corner."
        elif seg_type == 'straight':
            return "\nFocus on maximizing speed, optimal gear, and preparing for the next segment."
        elif seg_type == 'chicane':
            return "\nFocus on the best line and transitions through this chicane."
        # Fallback to situation-specific
        return self.get_situation_specific_request(situation, data)
    
    def get_situation_specific_request(self, situation: str, data: Dict[str, Any]) -> str:
        """Get situation-specific coaching request"""
        
        requests = {
            'insufficient_braking': """
Provide coaching advice for a driver who isn't using enough brake pressure. 
Focus on brake technique and confidence building.""",
            
            'early_throttle_in_corners': """
Provide coaching advice for a driver applying throttle too early in corners.
Focus on patience and corner exit technique.""",
            
            'inconsistent_lap_times': """
Provide coaching advice for improving consistency.
Focus on repeatable techniques and concentration.""",
            
            'sector_analysis': f"""
Provide coaching advice for sector improvement. The driver is losing time in sector {data.get('sector', 'unknown')}.
Focus areas: {', '.join(data.get('focus_areas', []))}.
Time deficit: {data.get('improvement_potential', 0):.2f} seconds.""",
            
            'corner_analysis': """
Provide detailed corner technique advice based on the telemetry data.
Focus on the specific corner and technique improvements.""",
            
            'race_strategy': """
Provide strategic racing advice considering the current race situation.
Focus on positioning, tire management, and race tactics.""",
            
            'understeer': """
Provide coaching advice for understeer correction.
Focus on weight transfer, brake technique, and line adjustment.""",
            
            'oversteer': """
Provide coaching advice for oversteer correction.
Focus on throttle control, steering technique, and car balance.""",
            
            'offtrack': """
Provide coaching advice for offtrack recovery and prevention.
Focus on track limits awareness and corner entry technique.""",
            
            'bad_exit': """
Provide coaching advice for improving corner exit speed.
Focus on apex timing, throttle application, and exit line.""",
            
            'missed_apex': """
Provide coaching advice for hitting the correct apex.
Focus on turn-in point, braking technique, and racing line."""
        }
        
        return requests.get(situation, """
Provide specific coaching advice based on the current situation and telemetry data.
Focus on the most important area for improvement.""")

class RemoteAICoach:
    """Remote AI coaching using OpenAI API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'gpt-3.5-turbo')
        self.max_requests_per_minute = config.get('max_requests_per_minute', 5)
        
        # Validate API key
        self.is_available_flag = bool(self.api_key and self.api_key != 'your-openai-api-key')
        
        # Rate limiting
        self.rate_limiter = RateLimiter(self.max_requests_per_minute, 60)
        
        # Prompt building
        self.prompt_builder = PromptBuilder()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0,
            'average_response_time': 0.0,
            'total_response_time': 0.0
        }
        
        logger.info(f"Remote AI Coach initialized (available: {self.is_available_flag})")
    
    def is_available(self) -> bool:
        """Check if the AI coach is available"""
        return self.is_available_flag and self.rate_limiter.can_make_request()
    
    async def generate_coaching(self, insight: Dict[str, Any], 
                              telemetry_data: Dict[str, Any], 
                              context: Any, current_segment: Any = None,
                              rich_context: Optional[EventContext] = None,
                              ml_analysis: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Generate coaching advice using AI, including segment/turn info, rich context, and ML analysis if available."""
        
        if not self.is_available():
            logger.debug("AI coach not available (API key or rate limit)")
            return None
        
        try:
            start_time = time.time()
            
            # Build prompt (now includes segment/turn info, rich context, and ML analysis)
            prompt = self.prompt_builder.build_prompt(
                insight, telemetry_data, context, 
                current_segment=current_segment, 
                rich_context=rich_context,
                ml_analysis=ml_analysis
            )
            
            # Make API request
            response = await self.make_api_request(prompt)
            
            if response:
                # Record successful request
                response_time = time.time() - start_time
                self.update_stats(True, response_time)
                
                return {
                    'message': response['content'],
                    'audio': response.get('audio'),
                    'category': self.categorize_response(response['content']),
                    'confidence': 0.9,  # AI responses have high confidence
                    'reasoning': response.get('reasoning', ''),
                    'response_time': response_time,
                    'rich_context_used': rich_context is not None
                }
            else:
                self.update_stats(False, 0)
                return None
                
        except Exception as e:
            logger.error(f"Error generating AI coaching: {e}")
            self.update_stats(False, 0)
            return None
    
    async def make_api_request(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 150) -> Optional[Dict[str, Any]]:
        """Make request to OpenAI API, then (optionally) generate audio using TTS endpoint."""
        
        if not self.rate_limiter.can_make_request():
            self.stats['rate_limited_requests'] += 1
            return None
        
        # Record the request
        self.rate_limiter.record_request()
        self.stats['total_requests'] += 1
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Use provided system prompt or default coaching prompt
        system_content = system_prompt if system_prompt is not None else 'You are an expert GT3 racing coach. Provide concise, actionable advice.'
        
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': system_content
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': max_tokens,  # Use provided token limit
            'temperature': 0.7,
            'presence_penalty': 0.1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        if 'choices' in result and len(result['choices']) > 0:
                            content = result['choices'][0]['message']['content'].strip()
                            # Now, generate audio using TTS endpoint
                            audio_data = None
                            try:
                                tts_headers = {
                                    'Authorization': f'Bearer {self.api_key}',
                                    'Content-Type': 'application/json'
                                }
                                tts_payload = {
                                    'model': 'tts-1',
                                    'input': content,
                                    'voice': 'alloy',
                                    'response_format': 'mp3'
                                }
                                async with session.post(
                                    'https://api.openai.com/v1/audio/speech',
                                    headers=tts_headers,
                                    json=tts_payload,
                                    timeout=aiohttp.ClientTimeout(total=15)
                                ) as tts_response:
                                    if tts_response.status == 200:
                                        audio_bytes = await tts_response.read()
                                        audio_data = base64.b64encode(audio_bytes).decode('utf-8')
                                        if audio_data:
                                            logger.info(f"TTS audio generated, length: {len(audio_data)} base64 chars")
                                            logger.info(f"TTS audio base64 (first 100 chars): {audio_data[:100]}")
                                        else:
                                            logger.warning("No audio data generated by TTS")
                                    else:
                                        error = await tts_response.text()
                                        logger.error(f"TTS error: {error}")
                            except Exception as tts_exc:
                                logger.error(f"TTS request failed: {tts_exc}")
                            return {
                                'content': content,
                                'audio': audio_data,
                                'model': self.model,
                                'tokens_used': result.get('usage', {}).get('total_tokens', 0)
                            }
                    else:
                        error_text = await response.text()
                        logger.error(f"API request failed: {response.status} - {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("OpenAI API request timed out.")
            return None
        except Exception as e:
            logger.error(f"API request error: {e}")
            return None
    
    async def generate_raw(self, prompt: str, system_prompt: str = "You are a helpful assistant.", max_tokens: int = 150) -> Optional[Dict[str, Any]]:
        """Generate raw response without coaching context"""
        
        if not self.is_available():
            logger.debug("AI coach not available (API key or rate limit)")
            return None
        
        try:
            start_time = time.time()
            
            # Make API request with custom system prompt and token limit
            response = await self.make_api_request(prompt, system_prompt, max_tokens)
            
            if response:
                # Record successful request
                response_time = time.time() - start_time
                self.update_stats(True, response_time)
                
                return {
                    'message': response['content'],
                    'category': 'raw_response',
                    'confidence': 0.9,
                    'response_time': response_time
                }
            else:
                self.update_stats(False, 0)
                return None
                
        except Exception as e:
            logger.error(f"Error generating raw response: {e}")
            self.update_stats(False, 0)
            return None
    
    def categorize_response(self, response_content: str) -> str:
        """Categorize AI response for message filtering"""
        content_lower = response_content.lower()
        
        if any(word in content_lower for word in ['brake', 'braking', 'slow down']):
            return 'braking'
        elif any(word in content_lower for word in ['throttle', 'accelerate', 'power']):
            return 'throttle'
        elif any(word in content_lower for word in ['corner', 'turn', 'apex', 'line']):
            return 'cornering'
        elif any(word in content_lower for word in ['consistent', 'smooth', 'steady']):
            return 'consistency'
        elif any(word in content_lower for word in ['strategy', 'tires', 'fuel', 'race']):
            return 'strategy'
        else:
            return 'ai_coaching'
    
    def update_stats(self, success: bool, response_time: float):
        """Update statistics"""
        if success:
            self.stats['successful_requests'] += 1
            self.stats['total_response_time'] += response_time
            self.stats['average_response_time'] = (
                self.stats['total_response_time'] / self.stats['successful_requests']
            )
        else:
            self.stats['failed_requests'] += 1
    
    def set_mode(self, mode):
        """Set coaching mode"""
        # Adjust AI parameters based on mode
        if mode.value == 'beginner':
            # More encouraging, simpler language
            pass
        elif mode.value == 'advanced':
            # More technical, specific advice
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get AI coach statistics"""
        success_rate = 0.0
        if self.stats['total_requests'] > 0:
            success_rate = self.stats['successful_requests'] / self.stats['total_requests']
        
        return {
            'is_available': self.is_available_flag,
            'success_rate': success_rate,
            'requests_remaining': self.max_requests_per_minute - len(self.rate_limiter.requests),
            **self.stats
        }

# Testing
async def test_remote_coach():
    """Test the remote AI coach"""
    config = {
        'api_key': 'your-test-api-key',  # Replace with real key for testing
        'model': 'gpt-3.5-turbo',
        'max_requests_per_minute': 2
    }
    
    coach = RemoteAICoach(config)
    
    # Test availability
    print(f"AI Coach available: {coach.is_available()}")
    
    # Test coaching generation (will fail without real API key)
    test_insight = {
        'situation': 'insufficient_braking',
        'confidence': 0.8,
        'data': {'brake_pressure': 45, 'corner': 'Turn 1'}
    }
    
    test_telemetry = {
        'speed': 120,
        'brake_pct': 45,
        'lap_distance_pct': 0.2
    }
    
    class MockContext:
        track_name = "Silverstone"
        car_name = "GT3 BMW"
        session_type = "Practice"
        coaching_mode = "Intermediate"
    
    context = MockContext()
    
    # This will not work without a real API key
    response = await coach.generate_coaching(test_insight, test_telemetry, context)
    
    if response:
        print(f"AI Coaching: {response['message']}")
    else:
        print("No AI response (expected without real API key)")
    
    print(f"Stats: {coach.get_stats()}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_remote_coach())
