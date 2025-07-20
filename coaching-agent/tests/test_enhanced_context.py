#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Enhanced Context Builder
============================

Tests the enhanced structured context builder with JSON output format.
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any

from enhanced_context_builder import EnhancedContextBuilder

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_enhanced_context_builder():
    """Test the enhanced context builder with structured JSON output"""
    logger.info("Testing Enhanced Context Builder...")
    
    # Initialize the builder
    builder = EnhancedContextBuilder({
        'buffer_duration': 30.0,
        'sample_rate': 60
    })
    
    # Simulate telemetry data over time
    for i in range(20):  # 20 samples
        telemetry = {
            'steering_angle': -5 + i * 0.5,
            'brake_pct': 30 + i * 2,
            'throttle_pct': 20 + i * 3,
            'gear': 3,
            'speed': 80 + i * 2,
            'rpm': 7000 + i * 100,
            'lap': 5,
            'fuelLevel': 25.0,
            'lapCurrentLapTime': 85.0 + i * 0.1,
            'tireTempLF': 80 + i,
            'tirePressureLF': 24.5 + i * 0.1
        }
        builder.add_telemetry(telemetry)
    
    # Build structured context
    context = builder.build_structured_context(
        event_type="understeer",
        severity="high",
        location={
            "track": "Spa",
            "turn": 5,
            "segment": "mid-corner"
        }
    )
    
    # Display the structured context
    logger.info("Generated Structured Context:")
    logger.info(json.dumps(context, indent=2))
    
    # Test specific sections
    logger.info(f"Event Type: {context['event']['type']}")
    logger.info(f"Severity: {context['event']['severity']}")
    logger.info(f"Location: {context['event']['location']}")
    logger.info(f"Driver Inputs: {len(context['driver_inputs']['steering_angle'])} samples")
    logger.info(f"Car State: {len(context['car_state']['speed_kph'])} samples")
    logger.info(f"History: {len(context['history'])} events")
    
    return context

def test_time_series_data():
    """Test time-series data extraction"""
    logger.info("Testing Time-Series Data Extraction...")
    
    builder = EnhancedContextBuilder()
    
    # Add telemetry with varying values
    for i in range(10):
        telemetry = {
            'steering_angle': -10 + i * 2,
            'brake_pct': 20 + i * 5,
            'throttle_pct': 10 + i * 8,
            'gear': 3,
            'speed': 70 + i * 3,
            'rpm': 6500 + i * 200,
            'tireTempLF': 75 + i * 2,
            'tirePressureLF': 24.0 + i * 0.2
        }
        builder.add_telemetry(telemetry)
    
    # Build context
    context = builder.build_structured_context(
        event_type="oversteer",
        severity="medium",
        location={"track": "Monza", "turn": 3, "segment": "exit"}
    )
    
    # Analyze time-series data
    steering_data = context['driver_inputs']['steering_angle']
    brake_data = context['driver_inputs']['brake']
    throttle_data = context['driver_inputs']['throttle']
    speed_data = context['car_state']['speed_kph']
    
    logger.info(f"Steering progression: {steering_data}")
    logger.info(f"Brake progression: {brake_data}")
    logger.info(f"Throttle progression: {throttle_data}")
    logger.info(f"Speed progression: {speed_data}")
    
    return context

def test_reference_data():
    """Test reference data calculation"""
    logger.info("Testing Reference Data Calculation...")
    
    builder = EnhancedContextBuilder()
    
    # Add telemetry with known values
    telemetry = {
        'speed': 95.0,  # ~153 kph
        'lapDeltaToBestLap': 0.5,
        'lapCurrentLapTime': 85.5,
        'lapBestLapTime': 85.0
    }
    
    context = builder.build_structured_context(
        event_type="bad_exit",
        severity="low",
        location={"track": "Silverstone", "turn": 4, "segment": "exit"}
    )
    
    reference = context['reference']
    logger.info(f"Reference Data: {reference}")
    
    # Verify calculations
    expected_speed = 95.0 * 1.60934  # Convert mph to kph
    logger.info(f"Expected speed: {expected_speed:.1f} kph")
    logger.info(f"Actual speed: {reference['driver_apex_speed']:.1f} kph")
    
    return context

def test_event_history():
    """Test event history tracking"""
    logger.info("Testing Event History Tracking...")
    
    builder = EnhancedContextBuilder()
    
    # Simulate multiple events
    events = [
        ("understeer", "medium", {"track": "Spa", "turn": 5, "segment": "entry"}),
        ("oversteer", "high", {"track": "Spa", "turn": 5, "segment": "mid-corner"}),
        ("understeer", "low", {"track": "Spa", "turn": 5, "segment": "exit"}),
        ("bad_exit", "medium", {"track": "Spa", "turn": 6, "segment": "exit"})
    ]
    
    for event_type, severity, location in events:
        telemetry = {
            'steering_angle': -5,
            'brake_pct': 30,
            'throttle_pct': 20,
            'gear': 3,
            'speed': 80,
            'rpm': 7000,
            'lap': 5
        }
        builder.add_telemetry(telemetry)
        
        context = builder.build_structured_context(
            event_type=event_type,
            severity=severity,
            location=location
        )
        
        logger.info(f"Event: {event_type} ({severity}) at {location['turn']}")
    
    # Check final history
    final_context = builder.build_structured_context(
        event_type="consistency",
        severity="medium",
        location={"track": "Spa", "turn": "all", "segment": "session"}
    )
    
    history = final_context['history']
    logger.info(f"Event History: {len(history)} events")
    for event in history:
        logger.info(f"  - Lap {event['lap']}, Turn {event['turn']}: {event['event']} ({event['severity']})")
    
    return final_context

def test_buffer_management():
    """Test buffer management and statistics"""
    logger.info("Testing Buffer Management...")
    
    builder = EnhancedContextBuilder({
        'buffer_duration': 10.0,  # 10 seconds
        'sample_rate': 60
    })
    
    # Add data to fill buffer
    for i in range(100):  # More than buffer capacity
        telemetry = {
            'steering_angle': -5 + (i % 10),
            'brake_pct': 30 + (i % 5),
            'throttle_pct': 20 + (i % 8),
            'gear': 3,
            'speed': 80 + (i % 15),
            'rpm': 7000 + (i % 20) * 100,
            'lap': 5
        }
        builder.add_telemetry(telemetry)
    
    # Get buffer stats
    stats = builder.get_buffer_stats()
    logger.info(f"Buffer Stats: {stats}")
    
    # Build context
    context = builder.build_structured_context(
        event_type="buffer_test",
        severity="medium",
        location={"track": "Test", "turn": 1, "segment": "test"}
    )
    
    # Check data lengths
    driver_inputs = context['driver_inputs']
    car_state = context['car_state']
    
    logger.info(f"Driver inputs: {len(driver_inputs['steering_angle'])} samples")
    logger.info(f"Car state: {len(car_state['speed_kph'])} samples")
    
    return context

def main():
    """Run all enhanced context tests"""
    logger.info("Starting Enhanced Context Tests...")
    
    # Test basic functionality
    context1 = test_enhanced_context_builder()
    
    # Test time-series data
    context2 = test_time_series_data()
    
    # Test reference data
    context3 = test_reference_data()
    
    # Test event history
    context4 = test_event_history()
    
    # Test buffer management
    context5 = test_buffer_management()
    
    logger.info("All enhanced context tests completed successfully!")
    
    # Show example output
    logger.info("\n=== EXAMPLE STRUCTURED CONTEXT ===")
    example = {
        "event": {
            "type": "understeer",
            "severity": "high",
            "location": {"track": "Spa", "turn": 5, "segment": "mid-corner"},
            "time": "14:30:25.123"
        },
        "driver_inputs": {
            "steering_angle": [-5, -6, -12, -14],
            "brake": [0.3, 0.4, 0.55, 0.3],
            "throttle": [0.1, 0.1, 0.15, 0.3],
            "gear": [3, 3, 2, 2]
        },
        "car_state": {
            "speed_kph": [98, 87, 80, 95],
            "rpm": [7100, 6900, 6700, 7200],
            "slip_angle": [-2, -6, -8, -7]
        },
        "tire_state": {
            "temps": [81, 80, 82, 85],
            "pressures": [24.5, 24.6, 24.7, 24.8]
        },
        "reference": {
            "best_apex_speed": 87,
            "driver_apex_speed": 80,
            "sector_delta_s": 0.18
        },
        "history": [
            {"lap": 5, "turn": 5, "event": "understeer", "severity": "medium"},
            {"lap": 6, "turn": 5, "event": "understeer", "severity": "high"}
        ],
        "session": {
            "type": "practice",
            "lap_number": 6,
            "fuel_remaining_l": 22
        }
    }
    
    logger.info(json.dumps(example, indent=2))

if __name__ == "__main__":
    main() 