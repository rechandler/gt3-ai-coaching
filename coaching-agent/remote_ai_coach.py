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

logger = logging.getLogger(__name__)

@dataclass
class AICoachingRequest:
    """Request for AI coaching"""
    insight: Dict[str, Any]
    telemetry_data: Dict[str, Any]
    context: Any  # CoachingContext
    timestamp: float

class RateLimiter:
    """Rate limiter for API requests"""
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    def can_make_request(self) -> bool:
        """Check if we can make a request"""
        current_time = time.time()
        
        # Remove old requests outside the time window
        while self.requests and current_time - self.requests[0] > self.time_window:
            self.requests.popleft()
        
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        """Record a new request"""
        self.requests.append(time.time())

class PromptBuilder:
    """Builds prompts for the AI based on context and situation"""
    
    def __init__(self):
        self.base_prompt = """You are an expert GT3 racing coach providing real-time coaching advice. 
You have access to detailed telemetry data and should provide specific, actionable advice.

Key principles:
- Be concise and clear (1-2 sentences max)
- Focus on the most important improvement
- Use racing terminology appropriately
- Be encouraging but direct
- Provide specific numeric feedback when relevant

Current session context:
Track: {track_name}
Car: {car_name}
Session Type: {session_type}
Coaching Mode: {coaching_mode}
"""
    
    def build_prompt(self, insight: Dict[str, Any], telemetry_data: Dict[str, Any], 
                    context: Any, current_segment: Any = None) -> str:
        """Build a prompt for the AI, including segment/turn info if available"""
        
        situation = insight.get('situation', 'general')
        confidence = insight.get('confidence', 0.0)
        data = insight.get('data', {})
        
        # Base context
        prompt = self.base_prompt.format(
            track_name=getattr(context, 'track_name', 'Unknown'),
            car_name=getattr(context, 'car_name', 'Unknown'),
            session_type=getattr(context, 'session_type', 'Practice'),
            coaching_mode=getattr(context, 'coaching_mode', 'Intermediate')
        )
        
        # Add segment/turn info if available
        if current_segment:
            seg_name = current_segment.get('name', 'Unknown')
            seg_num = current_segment.get('number', '')
            seg_range = current_segment.get('lap_percentage_range', None)
            prompt += f"\nCurrent segment/turn: {seg_name}"
            if seg_num:
                prompt += f" (#{seg_num})"
            if seg_range:
                prompt += f" (lap %: {seg_range[0]}-{seg_range[1]})"
            prompt += "\n"
            # Explicitly request segment/turn-specific advice
            prompt += "Provide coaching advice specific to this segment/turn, using its name and characteristics if possible.\n"
        
        # Add situation-specific context
        prompt += f"\nCurrent situation: {situation}\n"
        prompt += f"Confidence level: {confidence:.1%}\n"
        
        # Add telemetry context
        if telemetry_data:
            prompt += "\nCurrent telemetry:\n"
            relevant_keys = ['speed', 'brake_pct', 'throttle_pct', 'steering_angle', 
                           'lap_distance_pct', 'gear', 'rpm']
            for key in relevant_keys:
                if key in telemetry_data:
                    prompt += f"- {key}: {telemetry_data[key]}\n"
        
        # Add specific situation data
        if data:
            prompt += f"\nSituation details: {json.dumps(data, indent=2)}\n"
        
        # Add request for specific coaching
        prompt += self.get_situation_specific_request(situation, data)
        
        return prompt
    
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
Focus on positioning, tire management, and race tactics."""
        }
        
        return requests.get(situation, """
Provide general coaching advice based on the current situation and telemetry data.
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
                              context: Any, current_segment: Any = None) -> Optional[Dict[str, Any]]:
        """Generate coaching advice using AI, including segment/turn info if available"""
        
        if not self.is_available():
            logger.debug("AI coach not available (API key or rate limit)")
            return None
        
        try:
            start_time = time.time()
            
            # Build prompt (now includes segment/turn info)
            prompt = self.prompt_builder.build_prompt(insight, telemetry_data, context, current_segment=current_segment)
            
            # Make API request
            response = await self.make_api_request(prompt)
            
            if response:
                # Record successful request
                response_time = time.time() - start_time
                self.update_stats(True, response_time)
                
                return {
                    'message': response['content'],
                    'category': self.categorize_response(response['content']),
                    'confidence': 0.9,  # AI responses have high confidence
                    'reasoning': response.get('reasoning', ''),
                    'response_time': response_time
                }
            else:
                self.update_stats(False, 0)
                return None
                
        except Exception as e:
            logger.error(f"Error generating AI coaching: {e}")
            self.update_stats(False, 0)
            return None
    
    async def make_api_request(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Make request to OpenAI API"""
        
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
        
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are an expert GT3 racing coach. Provide concise, actionable advice.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 150,  # Keep responses concise
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
                            
                            return {
                                'content': content,
                                'model': self.model,
                                'tokens_used': result.get('usage', {}).get('total_tokens', 0)
                            }
                    else:
                        error_text = await response.text()
                        logger.error(f"API request failed: {response.status} - {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("API request timed out")
            return None
        except Exception as e:
            logger.error(f"API request error: {e}")
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
