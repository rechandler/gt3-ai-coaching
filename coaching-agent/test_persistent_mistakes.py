#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Persistent Mistake Tracking
================================

Demonstrates the persistent mistake tracking system with session summaries.
"""

import asyncio
import logging
import time
from mistake_tracker import MistakeTracker
from hybrid_coach import HybridCoachingAgent
from config import get_development_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_mistakes():
    """Create test mistake data to simulate a session"""
    return [
        # Turn 1 - Late braking (persistent issue)
        {
            'brake_timing_delta': 0.12,
            'throttle_timing_delta': 0.0,
            'apex_speed_delta': -3.0,
            'total_time_loss': 0.25,
            'detected_patterns': ['late_brake']
        },
        {
            'brake_timing_delta': 0.10,
            'throttle_timing_delta': 0.0,
            'apex_speed_delta': -2.5,
            'total_time_loss': 0.22,
            'detected_patterns': ['late_brake']
        },
        {
            'brake_timing_delta': 0.15,
            'throttle_timing_delta': 0.0,
            'apex_speed_delta': -4.0,
            'total_time_loss': 0.30,
            'detected_patterns': ['late_brake']
        },
        
        # Turn 8 - Low apex speed (persistent issue)
        {
            'brake_timing_delta': 0.0,
            'throttle_timing_delta': -0.08,
            'apex_speed_delta': -5.0,
            'total_time_loss': 0.28,
            'detected_patterns': ['late_throttle']
        },
        {
            'brake_timing_delta': 0.0,
            'throttle_timing_delta': -0.10,
            'apex_speed_delta': -6.0,
            'total_time_loss': 0.32,
            'detected_patterns': ['late_throttle']
        },
        {
            'brake_timing_delta': 0.0,
            'throttle_timing_delta': -0.12,
            'apex_speed_delta': -4.5,
            'total_time_loss': 0.29,
            'detected_patterns': ['late_throttle']
        },
        
        # Turn 3 - One-off mistake
        {
            'brake_timing_delta': 0.05,
            'throttle_timing_delta': 0.0,
            'apex_speed_delta': -2.0,
            'total_time_loss': 0.15,
            'detected_patterns': ['early_brake']
        },
        
        # Turn 5 - Understeer (persistent issue)
        {
            'brake_timing_delta': 0.0,
            'throttle_timing_delta': 0.0,
            'apex_speed_delta': -3.0,
            'total_time_loss': 0.20,
            'detected_patterns': ['understeer']
        },
        {
            'brake_timing_delta': 0.0,
            'throttle_timing_delta': 0.0,
            'apex_speed_delta': -2.5,
            'total_time_loss': 0.18,
            'detected_patterns': ['understeer']
        },
        {
            'brake_timing_delta': 0.0,
            'throttle_timing_delta': 0.0,
            'apex_speed_delta': -3.5,
            'total_time_loss': 0.22,
            'detected_patterns': ['understeer']
        }
    ]

async def test_persistent_mistake_tracking():
    """Test the persistent mistake tracking system"""
    logger.info("🧪 Testing Persistent Mistake Tracking")
    
    # Initialize coaching agent
    config = get_development_config()
    coaching_agent = HybridCoachingAgent(config)
    
    # Create test mistakes
    test_mistakes = create_test_mistakes()
    
    # Simulate processing mistakes over time
    corner_names = ["Turn 1", "Turn 8", "Turn 3", "Turn 5"]
    corner_index = 0
    
    for i, mistake_data in enumerate(test_mistakes):
        # Simulate telemetry with corner information
        telemetry = {
            'track_name': 'Spa-Francorchamps',
            'car_name': 'BMW M4 GT3',
            'session_type': 'practice',
            'lap': 1,
            'lap_distance_pct': 0.1 + (i * 0.1),
            'timestamp': time.time() + i
        }
        
        # Process through coaching agent
        coaching_agent.process_micro_analysis(telemetry)
        
        # Add mistake to tracker
        corner_name = corner_names[corner_index % len(corner_names)]
        corner_id = f"spa_francorchamps_{corner_name.lower().replace(' ', '_')}"
        
        coaching_agent.mistake_tracker.add_mistake(
            analysis_data=mistake_data,
            corner_id=corner_id,
            corner_name=corner_name
        )
        
        corner_index += 1
        
        # Small delay to simulate real-time processing
        await asyncio.sleep(0.1)
    
    # Get persistent mistakes
    persistent_mistakes = coaching_agent.get_persistent_mistakes()
    
    print("\n" + "="*60)
    print("📊 PERSISTENT MISTAKES ANALYSIS")
    print("="*60)
    
    for mistake in persistent_mistakes:
        print(f"🔍 {mistake['corner_name']}: {mistake['mistake_type']}")
        print(f"   Frequency: {mistake['frequency']} times")
        print(f"   Total time lost: {mistake['total_time_loss']:.2f}s")
        print(f"   Average time loss: {mistake['avg_time_loss']:.2f}s")
        print(f"   Priority: {mistake['priority']}")
        print(f"   Trend: {mistake['severity_trend']}")
        print(f"   Description: {mistake['description']}")
        print()
    
    # Get session summary
    session_summary = coaching_agent.get_session_summary()
    
    print("="*60)
    print("📈 SESSION SUMMARY")
    print("="*60)
    print(f"Session ID: {session_summary['session_id']}")
    print(f"Total mistakes: {session_summary['total_mistakes']}")
    print(f"Total time lost: {session_summary['total_time_lost']:.2f}s")
    print(f"Session score: {session_summary['session_score']:.2f}")
    print()
    
    print("🏆 Most Common Mistakes:")
    for mistake in session_summary['most_common_mistakes']:
        print(f"  • {mistake['corner_name']}: {mistake['mistake_type']} "
              f"({mistake['frequency']} times)")
    
    print("\n💰 Most Costly Mistakes:")
    for mistake in session_summary['most_costly_mistakes']:
        print(f"  • {mistake['corner_name']}: {mistake['total_time_loss']:.2f}s lost")
    
    print("\n🎯 Improvement Areas:")
    for area in session_summary['improvement_areas']:
        print(f"  • {area}")
    
    print("\n💡 Recommendations:")
    for rec in session_summary['recommendations']:
        print(f"  • {rec}")
    
    # Get focus areas
    print("\n" + "="*60)
    print("🎯 FOCUS AREAS")
    print("="*60)
    
    critical_areas = []
    high_priority_areas = []
    
    for mistake in persistent_mistakes:
        if mistake['priority'] == 'critical':
            critical_areas.append(mistake)
        elif mistake['priority'] == 'high':
            high_priority_areas.append(mistake)
    
    if critical_areas:
        print("🚨 CRITICAL FOCUS AREAS:")
        for area in critical_areas:
            print(f"  • {area['corner_name']}: {area['description']} "
                  f"({area['frequency']} times, {area['total_time_loss']:.1f}s lost)")
    
    if high_priority_areas:
        print("\n⚠️ HIGH PRIORITY AREAS:")
        for area in high_priority_areas:
            print(f"  • {area['corner_name']}: {area['description']} "
                  f"({area['frequency']} times, {area['total_time_loss']:.1f}s lost)")
    
    # Get corner-specific analysis
    print("\n" + "="*60)
    print("🔍 CORNER-SPECIFIC ANALYSIS")
    print("="*60)
    
    for corner_name in ["Turn 1", "Turn 8", "Turn 5"]:
        corner_id = f"spa_francorchamps_{corner_name.lower().replace(' ', '_')}"
        analysis = coaching_agent.get_corner_analysis(corner_id)
        
        if analysis:
            print(f"\n📍 {corner_name}:")
            print(f"   Total mistakes: {analysis['total_mistakes']}")
            print(f"   Total time lost: {analysis['total_time_lost']:.2f}s")
            print(f"   Recent trend: {analysis['recent_trend']}")
            
            for mistake_type, data in analysis['mistake_types'].items():
                print(f"   {data['description']}: {data['count']} times, "
                      f"{data['total_time_lost']:.2f}s lost")
    
    print("\n" + "="*60)
    print("✅ Persistent Mistake Tracking Test Complete")
    print("="*60)

def test_mistake_tracker_direct():
    """Test the mistake tracker directly"""
    logger.info("🔍 Testing Mistake Tracker Directly")
    
    tracker = MistakeTracker("test_session")
    
    # Add some test mistakes
    test_mistakes = [
        {
            'brake_timing_delta': 0.1,
            'total_time_loss': 0.25,
            'detected_patterns': ['late_brake']
        },
        {
            'brake_timing_delta': 0.08,
            'total_time_loss': 0.22,
            'detected_patterns': ['late_brake']
        },
        {
            'throttle_timing_delta': -0.1,
            'total_time_loss': 0.20,
            'detected_patterns': ['late_throttle']
        }
    ]
    
    for i, mistake_data in enumerate(test_mistakes):
        tracker.add_mistake(
            mistake_data,
            corner_id=f"turn_{i+1}",
            corner_name=f"Turn {i+1}"
        )
    
    # Get persistent mistakes
    persistent = tracker.get_persistent_mistakes()
    print(f"\nPersistent mistakes found: {len(persistent)}")
    
    for pattern in persistent:
        print(f"  {pattern.corner_name}: {pattern.mistake_type} "
              f"({pattern.frequency} times, {pattern.total_time_loss:.1f}s lost)")

if __name__ == "__main__":
    # Run tests
    asyncio.run(test_persistent_mistake_tracking())
    test_mistake_tracker_direct() 