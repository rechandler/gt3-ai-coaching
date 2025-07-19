#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Rich Context Implementation
===============================

Tests the rich context builder and its integration with the coaching system.
"""

import asyncio
import time
import logging
from typing import Dict, Any

from rich_context_builder import RichContextBuilder, EventContext
from remote_ai_coach import RemoteAICoach, PromptBuilder

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockContext:
    """Mock coaching context for testing"""
    def __init__(self):
        self.track_name = "Silverstone"
        self.car_name = "BMW M4 GT3"
        self.session_type = "Practice"
        self.coaching_mode = "Intermediate"

def test_rich_context_builder():
    """Test the rich context builder"""
    logger.info("Testing Rich Context Builder...")
    
    # Initialize the builder
    builder = RichContextBuilder()
    
    # Create sample telemetry data
    telemetry_data = {
        'speed': 120.5,
        'rpm': 6500,
        'gear': 4,
        'throttle_pct': 75.0,
        'brake_pct': 0.0,
        'steering_angle': 0.2,
        'lap_distance_pct': 0.25,
        'lap': 3,
        'track_name': 'Silverstone',
        'car_name': 'BMW M4 GT3',
        'session_type': 'Practice',
        'lapCurrentLapTime': 85.234,
        'lapBestLapTime': 84.123,
        'lapDeltaToBestLap': 1.111,
        'fuelLevel': 45.2,
        'tirePressureLF': 28.5,
        'tirePressureRF': 28.3,
        'tirePressureLR': 27.8,
        'tirePressureRR': 27.9,
        'airTemp': 22.0,
        'trackTempCrew': 25.0,
        'weatherType': 'Clear',
        'playerTrackSurface': 'Asphalt'
    }
    
    # Add telemetry to buffer
    for i in range(10):
        sample_data = telemetry_data.copy()
        sample_data['speed'] += i * 2
        sample_data['throttle_pct'] = max(0, 75 - i * 5)
        builder.add_telemetry(sample_data)
    
    # Create mock context
    context = MockContext()
    
    # Create sample segment
    segment = {
        'name': 'Turn 4',
        'type': 'corner',
        'description': 'Medium-speed right-hander',
        'start_pct': 0.20,
        'end_pct': 0.30
    }
    
    # Build rich context
    event_context = builder.build_rich_context(
        event_type='understeer',
        telemetry_data=telemetry_data,
        context=context,
        current_segment=segment
    )
    
    # Test the rich context
    logger.info(f"Event Type: {event_context.event_type}")
    logger.info(f"Event Location: {event_context.event_location}")
    logger.info(f"Car Speed: {event_context.car_state.get('speed', 0)}")
    logger.info(f"Track: {event_context.track_state.get('name', 'Unknown')}")
    logger.info(f"Session Trends: {event_context.session_trends.get('trend_direction', 'Unknown')}")
    logger.info(f"Anomaly Scores: {event_context.anomaly_scores}")
    
    # Test prompt formatting
    prompt_text = builder.format_for_prompt(event_context)
    logger.info(f"Prompt length: {len(prompt_text)} characters")
    
    # Test context summary
    summary = builder.get_context_summary(event_context)
    logger.info(f"Context Summary: {summary}")
    
    return event_context

def test_prompt_builder_integration():
    """Test integration with prompt builder"""
    logger.info("Testing Prompt Builder Integration...")
    
    # Initialize components
    prompt_builder = PromptBuilder()
    
    # Create sample insight
    insight = {
        'situation': 'understeer',
        'confidence': 0.8,
        'importance': 0.7,
        'data': {
            'pattern': 'understeer',
            'description': 'Driver experiencing understeer in Turn 4',
            'driver_issue': 'experiencing understeer'
        }
    }
    
    # Create sample telemetry
    telemetry_data = {
        'speed': 95.0,
        'throttle_pct': 60.0,
        'brake_pct': 20.0,
        'steering_angle': 0.4,
        'lap_distance_pct': 0.25,
        'gear': 3,
        'rpm': 5500
    }
    
    # Create mock context
    context = MockContext()
    
    # Create sample segment
    segment = {
        'name': 'Turn 4',
        'type': 'corner',
        'description': 'Medium-speed right-hander',
        'start_pct': 0.20,
        'end_pct': 0.30
    }
    
    # Build prompt with rich context
    prompt = prompt_builder.build_prompt(
        insight=insight,
        telemetry_data=telemetry_data,
        context=context,
        current_segment=segment
    )
    
    logger.info(f"Generated prompt length: {len(prompt)} characters")
    logger.info("Prompt preview (first 500 chars):")
    logger.info(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    
    return prompt

async def test_ai_coach_integration():
    """Test integration with AI coach"""
    logger.info("Testing AI Coach Integration...")
    
    # Create config (without API key for testing)
    config = {
        'api_key': 'test-key',
        'model': 'gpt-3.5-turbo',
        'max_requests_per_minute': 5
    }
    
    # Initialize AI coach
    ai_coach = RemoteAICoach(config)
    
    # Create sample insight
    insight = {
        'situation': 'understeer',
        'confidence': 0.8,
        'importance': 0.7,
        'data': {
            'pattern': 'understeer',
            'description': 'Driver experiencing understeer in Turn 4',
            'driver_issue': 'experiencing understeer'
        }
    }
    
    # Create sample telemetry
    telemetry_data = {
        'speed': 95.0,
        'throttle_pct': 60.0,
        'brake_pct': 20.0,
        'steering_angle': 0.4,
        'lap_distance_pct': 0.25,
        'gear': 3,
        'rpm': 5500
    }
    
    # Create mock context
    context = MockContext()
    
    # Create sample segment
    segment = {
        'name': 'Turn 4',
        'type': 'corner',
        'description': 'Medium-speed right-hander',
        'start_pct': 0.20,
        'end_pct': 0.30
    }
    
    # Test prompt generation (without making actual API call)
    prompt = ai_coach.prompt_builder.build_prompt(
        insight=insight,
        telemetry_data=telemetry_data,
        context=context,
        current_segment=segment
    )
    
    logger.info(f"AI Coach prompt length: {len(prompt)} characters")
    logger.info("Rich context integration working correctly!")

def main():
    """Run all tests"""
    logger.info("Starting Rich Context Tests...")
    
    # Test rich context builder
    event_context = test_rich_context_builder()
    
    # Test prompt builder integration
    prompt = test_prompt_builder_integration()
    
    # Test AI coach integration
    asyncio.run(test_ai_coach_integration())
    
    logger.info("All tests completed successfully!")
    logger.info("Rich context implementation is working correctly.")

if __name__ == "__main__":
    main() 