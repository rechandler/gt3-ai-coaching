#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Reference Lap System
========================

Demonstrates the professional coaching system with reference lap comparisons.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from reference_manager import ReferenceManager, ReferenceLap, ReferenceSegment
from hybrid_coach import HybridCoachingAgent
from config import get_development_config

def create_sample_telemetry(lap_progress: float, speed: float = 120.0) -> Dict[str, Any]:
    """Create sample telemetry data"""
    return {
        'timestamp': time.time(),
        'speed': speed,
        'brake_pct': 80 if lap_progress < 0.1 else 0,
        'throttle_pct': 20 if lap_progress < 0.1 else 85,
        'steering_angle': 0.3 if 0.05 < lap_progress < 0.15 else 0.0,
        'lap_distance_pct': lap_progress,
        'lapCurrentLapTime': 85.0 + lap_progress * 10,
        'track_name': 'Spa-Francorchamps',
        'car_name': 'BMW M4 GT3',
        'session_type': 'practice'
    }

def create_sample_reference_lap() -> ReferenceLap:
    """Create a sample reference lap for testing"""
    segments = {
        's1': ReferenceSegment(
            segment_id='s1',
            segment_name='Sector 1',
            start_pct=0.0,
            end_pct=0.33,
            segment_time=28.5,
            entry_speed=120.0,
            exit_speed=110.0,
            min_speed=80.0,
            max_speed=130.0,
            avg_throttle=60.0,
            avg_brake=40.0,
            max_steering=0.4,
            racing_line_score=0.85,
            optimal_inputs={
                'optimal_entry_speed': 125.0,
                'optimal_exit_speed': 115.0,
                'optimal_throttle_application': 70.0,
                'optimal_brake_release': 20.0
            }
        ),
        's2': ReferenceSegment(
            segment_id='s2',
            segment_name='Sector 2',
            start_pct=0.33,
            end_pct=0.66,
            segment_time=29.0,
            entry_speed=110.0,
            exit_speed=125.0,
            min_speed=90.0,
            max_speed=140.0,
            avg_throttle=80.0,
            avg_brake=20.0,
            max_steering=0.3,
            racing_line_score=0.90,
            optimal_inputs={
                'optimal_entry_speed': 115.0,
                'optimal_exit_speed': 130.0,
                'optimal_throttle_application': 85.0,
                'optimal_brake_release': 15.0
            }
        ),
        's3': ReferenceSegment(
            segment_id='s3',
            segment_name='Sector 3',
            start_pct=0.66,
            end_pct=1.0,
            segment_time=27.5,
            entry_speed=125.0,
            exit_speed=135.0,
            min_speed=100.0,
            max_speed=150.0,
            avg_throttle=90.0,
            avg_brake=10.0,
            max_steering=0.2,
            racing_line_score=0.88,
            optimal_inputs={
                'optimal_entry_speed': 130.0,
                'optimal_exit_speed': 140.0,
                'optimal_throttle_application': 95.0,
                'optimal_brake_release': 5.0
            }
        )
    }
    
    return ReferenceLap(
        track_name='Spa-Francorchamps',
        car_name='BMW M4 GT3',
        lap_time=85.0,
        lap_type='personal_best',
        timestamp=time.time(),
        segments=segments,
        metadata={
            'created_by': 'test_script',
            'description': 'Sample reference lap for testing'
        }
    )

async def test_reference_manager():
    """Test the reference manager functionality"""
    logger.info("🧪 Testing Reference Manager...")
    
    # Initialize reference manager
    ref_manager = ReferenceManager("test_reference_data")
    
    # Create and save a reference lap
    reference_lap = create_sample_reference_lap()
    success = ref_manager.save_reference_lap(reference_lap)
    logger.info(f"✅ Reference lap saved: {success}")
    
    # Load reference laps
    loaded = ref_manager.load_reference_laps('Spa-Francorchamps', 'BMW M4 GT3')
    logger.info(f"✅ Reference laps loaded: {loaded}")
    
    # Test reference context generation
    test_telemetry = create_sample_telemetry(0.1, 115.0)
    context = ref_manager.get_reference_context(test_telemetry)
    logger.info(f"📊 Reference context: {context}")
    
    # Test delta analysis
    delta_analysis = ref_manager.calculate_delta_analysis(test_telemetry, 'personal_best')
    if delta_analysis:
        logger.info(f"📈 Delta analysis: {delta_analysis}")
    
    return ref_manager

async def test_hybrid_coach_with_references():
    """Test the hybrid coach with reference lap integration"""
    logger.info("🧪 Testing Hybrid Coach with References...")
    
    # Initialize coaching agent
    config = get_development_config()
    agent = HybridCoachingAgent(config)
    
    # Create sample telemetry
    telemetry_data = create_sample_telemetry(0.1, 110.0)
    
    # Process telemetry through the agent
    await agent.process_telemetry(telemetry_data)
    
    # Get stats
    stats = agent.get_stats()
    logger.info(f"📊 Agent stats: {stats}")
    
    return agent

async def test_reference_coaching_messages():
    """Test coaching messages with reference comparisons"""
    logger.info("🧪 Testing Reference Coaching Messages...")
    
    # Initialize components
    ref_manager = ReferenceManager("test_reference_data")
    
    # Create reference lap
    reference_lap = create_sample_reference_lap()
    ref_manager.save_reference_lap(reference_lap)
    
    # Test different scenarios
    scenarios = [
        {'progress': 0.05, 'speed': 100.0, 'description': 'Slow entry speed'},
        {'progress': 0.15, 'speed': 105.0, 'description': 'Poor exit speed'},
        {'progress': 0.35, 'speed': 115.0, 'description': 'Good sector 2'},
        {'progress': 0.70, 'speed': 125.0, 'description': 'Final sector'}
    ]
    
    for scenario in scenarios:
        telemetry = create_sample_telemetry(scenario['progress'], scenario['speed'])
        context = ref_manager.get_reference_context(telemetry)
        
        logger.info(f"🎯 {scenario['description']}")
        logger.info(f"   Current speed: {scenario['speed']:.1f}")
        logger.info(f"   Reference available: {context.get('reference_available', False)}")
        if context.get('reference_available'):
            logger.info(f"   Delta to reference: {context.get('delta_to_reference', 0):.2f}s")
            logger.info(f"   Improvement potential: {context.get('improvement_potential', 0):.2f}s")

async def main():
    """Main test function"""
    logger.info("🚀 Starting Reference System Tests...")
    
    try:
        # Test reference manager
        ref_manager = await test_reference_manager()
        
        # Test hybrid coach integration
        agent = await test_hybrid_coach_with_references()
        
        # Test coaching messages
        await test_reference_coaching_messages()
        
        logger.info("✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 