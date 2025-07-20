#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Micro Analysis System
==========================

Demonstrates the micro-analysis system with specific timing and speed delta feedback.
"""

import asyncio
import logging
from micro_analysis import MicroAnalyzer, ReferenceDataManager, CornerReference
from hybrid_coach import HybridCoachingAgent
from config import get_development_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_corner_reference():
    """Create a test corner reference for Spa-Francorchamps Eau Rouge"""
    return CornerReference(
        corner_id="spa_francorchamps_eau_rouge",
        corner_name="Eau Rouge",
        track_name="Spa-Francorchamps",
        position_start=0.03,
        position_end=0.08,
        reference_brake_point=0.035,
        reference_brake_pressure=70.0,
        reference_entry_speed=140.0,
        reference_apex_speed=95.0,
        reference_exit_speed=135.0,
        reference_throttle_point=0.065,
        reference_throttle_pressure=85.0,
        reference_steering_angle=0.4,
        reference_racing_line=[
            (0.03, 0.0), (0.035, 0.2), (0.04, 0.4), (0.045, 0.4),
            (0.05, 0.3), (0.055, 0.2), (0.06, 0.1), (0.065, 0.0),
            (0.07, 0.0), (0.075, 0.0), (0.08, 0.0)
        ],
        reference_corner_time=4.2,
        reference_gear=4,
        corner_type="high_speed",
        difficulty="hard",
        notes="Famous uphill left-right complex"
    )

def create_test_corner_data():
    """Create test corner data with specific issues"""
    return [
        # Entry - slightly late braking
        {'speed': 138, 'brake': 0, 'throttle': 85, 'steering': 0.0, 'lap_distance_pct': 0.03, 'gear': 5},
        {'speed': 135, 'brake': 60, 'throttle': 0, 'steering': 0.2, 'lap_distance_pct': 0.035, 'gear': 4},
        {'speed': 125, 'brake': 75, 'throttle': 0, 'steering': 0.4, 'lap_distance_pct': 0.04, 'gear': 4},
        {'speed': 110, 'brake': 80, 'throttle': 0, 'steering': 0.45, 'lap_distance_pct': 0.045, 'gear': 3},
        # Apex - speed too low
        {'speed': 90, 'brake': 40, 'throttle': 20, 'steering': 0.4, 'lap_distance_pct': 0.05, 'gear': 3},
        {'speed': 88, 'brake': 20, 'throttle': 40, 'steering': 0.3, 'lap_distance_pct': 0.055, 'gear': 3},
        # Exit - late throttle application
        {'speed': 95, 'brake': 0, 'throttle': 60, 'steering': 0.2, 'lap_distance_pct': 0.06, 'gear': 4},
        {'speed': 105, 'brake': 0, 'throttle': 70, 'steering': 0.1, 'lap_distance_pct': 0.065, 'gear': 4},
        {'speed': 115, 'brake': 0, 'throttle': 80, 'steering': 0.0, 'lap_distance_pct': 0.07, 'gear': 4},
        {'speed': 125, 'brake': 0, 'throttle': 90, 'steering': 0.0, 'lap_distance_pct': 0.075, 'gear': 5},
        {'speed': 130, 'brake': 0, 'throttle': 95, 'steering': 0.0, 'lap_distance_pct': 0.08, 'gear': 5}
    ]

def create_good_corner_data():
    """Create test corner data with good technique"""
    return [
        # Entry - proper braking
        {'speed': 140, 'brake': 0, 'throttle': 85, 'steering': 0.0, 'lap_distance_pct': 0.03, 'gear': 5},
        {'speed': 135, 'brake': 70, 'throttle': 0, 'steering': 0.2, 'lap_distance_pct': 0.035, 'gear': 4},
        {'speed': 120, 'brake': 75, 'throttle': 0, 'steering': 0.4, 'lap_distance_pct': 0.04, 'gear': 4},
        {'speed': 105, 'brake': 80, 'throttle': 0, 'steering': 0.4, 'lap_distance_pct': 0.045, 'gear': 3},
        # Apex - good speed
        {'speed': 95, 'brake': 30, 'throttle': 30, 'steering': 0.4, 'lap_distance_pct': 0.05, 'gear': 3},
        {'speed': 98, 'brake': 10, 'throttle': 50, 'steering': 0.3, 'lap_distance_pct': 0.055, 'gear': 3},
        # Exit - early throttle
        {'speed': 105, 'brake': 0, 'throttle': 70, 'steering': 0.2, 'lap_distance_pct': 0.06, 'gear': 4},
        {'speed': 115, 'brake': 0, 'throttle': 85, 'steering': 0.1, 'lap_distance_pct': 0.065, 'gear': 4},
        {'speed': 125, 'brake': 0, 'throttle': 90, 'steering': 0.0, 'lap_distance_pct': 0.07, 'gear': 4},
        {'speed': 135, 'brake': 0, 'throttle': 95, 'steering': 0.0, 'lap_distance_pct': 0.075, 'gear': 5},
        {'speed': 140, 'brake': 0, 'throttle': 100, 'steering': 0.0, 'lap_distance_pct': 0.08, 'gear': 5}
    ]

async def test_micro_analysis():
    """Test the micro-analysis system"""
    logger.info("🧪 Testing Micro Analysis System")
    
    # Initialize micro-analyzer
    reference_manager = ReferenceDataManager()
    micro_analyzer = MicroAnalyzer(reference_manager)
    
    # Create test reference
    test_reference = create_test_corner_reference()
    reference_manager.add_corner_reference(test_reference)
    
    # Test with poor technique
    logger.info("📊 Testing with poor technique...")
    poor_corner_data = create_test_corner_data()
    
    analysis_poor = micro_analyzer.perform_micro_analysis(poor_corner_data, test_reference)
    
    print("\n" + "="*60)
    print("📉 POOR TECHNIQUE ANALYSIS")
    print("="*60)
    print(f"Corner: {analysis_poor.corner_name}")
    print(f"Total time loss: {analysis_poor.total_time_loss:.2f}s")
    print(f"Brake timing delta: {analysis_poor.brake_timing_delta:.2f}s")
    print(f"Throttle timing delta: {analysis_poor.throttle_timing_delta:.2f}s")
    print(f"Apex speed delta: {analysis_poor.apex_speed_delta:.1f} km/h")
    print(f"Detected patterns: {analysis_poor.detected_patterns}")
    print(f"Priority: {analysis_poor.priority}")
    print("\nSpecific feedback:")
    for feedback in analysis_poor.specific_feedback:
        print(f"  • {feedback}")
    
    # Test with good technique
    logger.info("📊 Testing with good technique...")
    good_corner_data = create_good_corner_data()
    
    analysis_good = micro_analyzer.perform_micro_analysis(good_corner_data, test_reference)
    
    print("\n" + "="*60)
    print("📈 GOOD TECHNIQUE ANALYSIS")
    print("="*60)
    print(f"Corner: {analysis_good.corner_name}")
    print(f"Total time loss: {analysis_good.total_time_loss:.2f}s")
    print(f"Brake timing delta: {analysis_good.brake_timing_delta:.2f}s")
    print(f"Throttle timing delta: {analysis_good.throttle_timing_delta:.2f}s")
    print(f"Apex speed delta: {analysis_good.apex_speed_delta:.1f} km/h")
    print(f"Detected patterns: {analysis_good.detected_patterns}")
    print(f"Priority: {analysis_good.priority}")
    print("\nSpecific feedback:")
    for feedback in analysis_good.specific_feedback:
        print(f"  • {feedback}")
    
    # Test integration with coaching agent
    logger.info("🤖 Testing integration with coaching agent...")
    config = get_development_config()
    coaching_agent = HybridCoachingAgent(config)
    
    # Simulate telemetry processing
    for i, telemetry in enumerate(poor_corner_data):
        # Add required fields for coaching agent
        telemetry.update({
            'track_name': 'Spa-Francorchamps',
            'car_name': 'BMW M4 GT3',
            'session_type': 'practice',
            'lap': 1,
            'timestamp': i * 0.1
        })
        
        # Process through coaching agent
        coaching_agent.process_micro_analysis(telemetry)
    
    # Get insights
    insights = coaching_agent.get_micro_analysis_insights()
    
    print("\n" + "="*60)
    print("🤖 COACHING AGENT INTEGRATION")
    print("="*60)
    if insights:
        for insight in insights:
            print(f"Type: {insight['type']}")
            print(f"Confidence: {insight['confidence']}")
            print(f"Severity: {insight['severity']}")
            print(f"Message: {insight['message']}")
            print(f"Data: {insight['data']}")
    else:
        print("No insights generated yet (corner analysis may not be complete)")
    
    print("\n" + "="*60)
    print("✅ Micro Analysis Test Complete")
    print("="*60)

def test_pattern_classification():
    """Test pattern classification with different scenarios"""
    logger.info("🔍 Testing Pattern Classification")
    
    from micro_analysis import PatternClassifier
    
    classifier = PatternClassifier()
    
    # Test late apex pattern
    late_apex_data = [
        {'speed': 120, 'brake': 0, 'throttle': 80, 'steering': 0.0, 'lap_distance_pct': 0.25},
        {'speed': 100, 'brake': 60, 'throttle': 0, 'steering': 0.2, 'lap_distance_pct': 0.26},
        {'speed': 80, 'brake': 80, 'throttle': 0, 'steering': 0.4, 'lap_distance_pct': 0.27},
        {'speed': 70, 'brake': 40, 'throttle': 20, 'steering': 0.5, 'lap_distance_pct': 0.28},  # Late apex
        {'speed': 75, 'brake': 0, 'throttle': 60, 'steering': 0.3, 'lap_distance_pct': 0.29},
        {'speed': 90, 'brake': 0, 'throttle': 80, 'steering': 0.1, 'lap_distance_pct': 0.30}
    ]
    
    reference = CornerReference(
        corner_id="test_corner",
        corner_name="Test Corner",
        track_name="Test Track",
        position_start=0.25,
        position_end=0.30,
        reference_brake_point=0.255,
        reference_throttle_point=0.27,  # Earlier than actual
        reference_brake_pressure=70,
        reference_entry_speed=120,
        reference_apex_speed=75,
        reference_exit_speed=95,
        reference_throttle_pressure=80,
        reference_steering_angle=0.5,
        reference_racing_line=[],
        reference_corner_time=5.0,
        reference_gear=3,
        corner_type="medium",
        difficulty="medium"
    )
    
    patterns, confidence = classifier.classify_patterns(late_apex_data, reference)
    
    print(f"\nLate Apex Test:")
    print(f"Detected patterns: {patterns}")
    print(f"Confidence scores: {confidence}")

if __name__ == "__main__":
    # Run tests
    asyncio.run(test_micro_analysis())
    test_pattern_classification() 