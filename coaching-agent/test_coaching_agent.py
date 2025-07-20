#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Suite for the Hybrid Coaching Agent
"""

import asyncio
import pytest
import logging
import sys
import os

# Add the coaching-agent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hybrid_coach import HybridCoachingAgent
from local_ml_coach import LocalMLCoach
from message_queue import CoachingMessageQueue, CoachingMessage, MessagePriority
from telemetry_analyzer import TelemetryAnalyzer
from session_manager import SessionManager
from config import ConfigManager

# Configure logging for tests
logging.basicConfig(level=logging.INFO)

@pytest.fixture
def test_config():
    """Test configuration"""
    return {
        'local_config': {
            'model_path': 'test_models/',
            'confidence_threshold': 0.7
        },
        'remote_config': {
            'api_key': 'test-key',  # Will not actually call API
            'model': 'gpt-3.5-turbo',
            'max_requests_per_minute': 5
        },
        'coaching_config': {
            'enable_ai_coaching': False,  # Disable for testing
            'enable_local_coaching': True
        }
    }

@pytest.fixture
def sample_telemetry():
    """Sample telemetry data"""
    return {
        'speed': 120,
        'brake_pct': 30,
        'throttle_pct': 70,
        'steering_angle': 0.2,
        'lap_distance_pct': 0.3,
        'gear': 4,
        'rpm': 6000,
        'track_name': 'Test Track',
        'car_name': 'BMW M4 GT3',
        'session_type': 'practice'
    }

class TestMessageQueue:
    """Test the message queue system"""
    
    @pytest.mark.asyncio
    async def test_message_priority(self):
        """Test message priority ordering"""
        queue = CoachingMessageQueue()
        
        # Add messages with different priorities
        messages = [
            CoachingMessage(
                content="Low priority message",
                category="general",
                priority=MessagePriority.LOW,
                source="test",
                confidence=0.5,
                context="test",
                timestamp=0
            ),
            CoachingMessage(
                content="Critical message",
                category="safety",
                priority=MessagePriority.CRITICAL,
                source="test",
                confidence=1.0,
                context="test",
                timestamp=0
            ),
            CoachingMessage(
                content="High priority message",
                category="braking",
                priority=MessagePriority.HIGH,
                source="test",
                confidence=0.8,
                context="test",
                timestamp=0
            )
        ]
        
        # Add in random order
        for msg in messages:
            await queue.add_message(msg)
        
        # Should come out in priority order (CRITICAL, HIGH, LOW)
        first = await queue.get_next_message()
        assert first.priority == MessagePriority.CRITICAL
        
        second = await queue.get_next_message()
        assert second.priority == MessagePriority.HIGH
        
        third = await queue.get_next_message()
        assert third.priority == MessagePriority.LOW
    
    @pytest.mark.asyncio
    async def test_duplicate_filtering(self):
        """Test duplicate message filtering"""
        queue = CoachingMessageQueue()
        
        # Create two similar messages
        msg1 = CoachingMessage(
            content="Brake earlier for turn 1",
            category="braking",
            priority=MessagePriority.MEDIUM,
            source="test",
            confidence=0.8,
            context="test",
            timestamp=0
        )
        
        msg2 = CoachingMessage(
            content="Brake earlier for turn 1",
            category="braking",
            priority=MessagePriority.MEDIUM,
            source="test",
            confidence=0.8,
            context="test",
            timestamp=0
        )
        
        # Add both messages
        result1 = await queue.add_message(msg1)
        result2 = await queue.add_message(msg2)  # Should be filtered
        
        assert result1 == True  # First message added
        assert result2 == False  # Second message filtered
        
        # Only one message should be in queue
        assert queue.get_queue_size() == 1

class TestLocalMLCoach:
    """Test the local ML coach"""
    
    @pytest.mark.asyncio
    async def test_telemetry_analysis(self, test_config, sample_telemetry):
        """Test telemetry analysis"""
        coach = LocalMLCoach(test_config['local_config'])
        
        # Analyze telemetry
        insights = await coach.analyze(sample_telemetry, {})
        
        # Should return a list of insights
        assert isinstance(insights, list)
    
    @pytest.mark.asyncio
    async def test_message_generation(self, test_config):
        """Test message generation"""
        coach = LocalMLCoach(test_config['local_config'])
        
        # Create test insight
        insight = {
            'situation': 'insufficient_braking',
            'confidence': 0.8,
            'importance': 0.6,
            'data': {'brake_pressure': 45}
        }
        
        # Generate message
        message = await coach.generate_message(insight)
        
        # Should return a message
        assert message is not None
        assert 'message' in message
        assert 'category' in message
        assert len(message['message']) > 0

class TestTelemetryAnalyzer:
    """Test the telemetry analyzer"""
    
    def test_motion_calculation(self, sample_telemetry):
        """Test motion calculations"""
        analyzer = TelemetryAnalyzer()
        
        # First analysis (no previous data)
        analysis1 = analyzer.analyze(sample_telemetry)
        assert 'motion' in analysis1
        
        # Second analysis (with previous data)
        sample_telemetry['speed'] = 130  # Changed speed
        analysis2 = analyzer.analyze(sample_telemetry)
        
        # Should have motion data now
        assert 'longitudinal' in analysis2['motion']
    
    def test_sector_analysis(self, sample_telemetry):
        """Test sector analysis"""
        analyzer = TelemetryAnalyzer()
        
        # Simulate moving through sectors
        positions = [0.1, 0.35, 0.65, 0.95]
        
        for pos in positions:
            sample_telemetry['lap_distance_pct'] = pos
            analysis = analyzer.analyze(sample_telemetry)
            
            # Check if sector analysis is present when crossing boundaries
            if analysis.get('sector'):
                assert 'sector' in analysis['sector']
                assert 'sector_time' in analysis['sector']

class TestSessionManager:
    """Test the session manager"""
    
    def test_session_lifecycle(self):
        """Test session start/end"""
        manager = SessionManager("test_sessions")
        
        # Start session
        session_id = manager.start_session(
            track_name="Test Track",
            car_name="Test Car",
            session_type="practice"
        )
        
        assert session_id is not None
        assert manager.is_active
        
        # Add some lap data
        manager.add_lap_data(90.5, [30.0, 30.0, 30.5])
        manager.add_lap_data(89.8, [29.5, 30.0, 30.3])
        
        # Get stats
        stats = manager.get_session_stats()
        assert stats['metrics']['total_laps'] == 2
        
        # End session
        ended_session = manager.end_session()
        assert ended_session is not None
        assert not manager.is_active

class TestHybridCoach:
    """Test the hybrid coaching agent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, test_config):
        """Test agent initialization"""
        agent = HybridCoachingAgent(test_config)
        
        # Check components are initialized
        assert agent.local_coach is not None
        assert agent.remote_coach is not None
        assert agent.message_queue is not None
        assert agent.telemetry_analyzer is not None
        assert agent.session_manager is not None
    
    @pytest.mark.asyncio
    async def test_telemetry_processing(self, test_config, sample_telemetry):
        """Test telemetry processing"""
        agent = HybridCoachingAgent(test_config)
        
        # Process telemetry (should not crash)
        await agent.process_telemetry(sample_telemetry)
        
        # Agent should have processed the data
        # (Specific assertions depend on implementation details)
    
    def test_get_stats(self, test_config):
        """Test statistics retrieval"""
        agent = HybridCoachingAgent(test_config)
        
        stats = agent.get_stats()
        
        # Should return statistics dictionary
        assert isinstance(stats, dict)
        assert 'is_active' in stats
        assert 'context' in stats

class TestConfiguration:
    """Test configuration management"""
    
    def test_config_manager_initialization(self):
        """Test config manager"""
        manager = ConfigManager()
        
        config = manager.get_config()
        assert isinstance(config, dict)
        assert 'local_config' in config
        assert 'remote_config' in config
    
    def test_track_config(self):
        """Test track-specific configuration"""
        manager = ConfigManager()
        
        # Test known track
        silverstone_config = manager.get_track_config("Silverstone")
        assert 'sector_boundaries' in silverstone_config
        
        # Test unknown track (should return defaults)
        unknown_config = manager.get_track_config("Unknown Track")
        assert 'sector_boundaries' in unknown_config
    
    def test_mode_config(self):
        """Test coaching mode configuration"""
        manager = ConfigManager()
        
        beginner_config = manager.get_mode_config("beginner")
        assert 'ai_usage_frequency' in beginner_config
        assert beginner_config['message_tone'] == 'encouraging'

def test_prompt_builder_includes_category():
    from remote_ai_coach import PromptBuilder
    builder = PromptBuilder()
    # Simulate context with category
    class Context:
        track_name = "Spa-Francorchamps"
        car_name = "BMW M4 GT3"
        category = "SportsCar"
        session_type = "Practice"
        coaching_mode = "Intermediate"
    context = Context()
    insight = {'situation': 'inconsistent_lap_times', 'confidence': 0.8, 'importance': 0.6, 'data': {}}
    telemetry_data = {}
    prompt = builder.build_prompt(insight, telemetry_data, context)
    assert "Category: SportsCar" in prompt
    assert "You are an expert SportsCar racing coach" in prompt

# Integration test
class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, test_config, sample_telemetry):
        """Test complete workflow"""
        # Create agent
        agent = HybridCoachingAgent(test_config)
        
        # Process multiple telemetry samples
        telemetry_samples = []
        for i in range(10):
            sample = sample_telemetry.copy()
            sample['lap_distance_pct'] = i * 0.1  # Progress through lap
            sample['speed'] = 120 - (i * 5) if i < 5 else 100 + (i * 5)  # Vary speed
            telemetry_samples.append(sample)
        
        # Process all samples
        for sample in telemetry_samples:
            await agent.process_telemetry(sample)
        
        # Get final stats
        stats = agent.get_stats()
        
        # Should have processed telemetry
        assert isinstance(stats, dict)

# Run tests
def run_tests():
    """Run all tests"""
    pytest.main([__file__, "-v", "--tb=short"])

if __name__ == "__main__":
    run_tests()
