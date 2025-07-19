#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Context Builder for GT3 AI Coaching
============================================

Implements structured JSON context with time-series data aggregation
and sliding window buffers for comprehensive coaching insights.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
import json
import math

logger = logging.getLogger(__name__)

@dataclass
class TimeSeriesPoint:
    """A single time-series data point"""
    timestamp: float
    steering_angle: float
    brake: float
    throttle: float
    gear: int
    speed_kph: float
    rpm: int
    slip_angle: Optional[float] = None
    tire_temp: Optional[float] = None
    tire_pressure: Optional[float] = None

class EnhancedContextBuilder:
    """
    Enhanced context builder with structured JSON output and time-series aggregation.
    
    Features:
    - Sliding window buffers (10-30s)
    - Time-series data aggregation
    - Structured JSON context
    - Event severity analysis
    - Reference data comparison
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Buffer settings
        self.buffer_duration = config.get('buffer_duration', 30.0)  # 30 seconds
        self.sample_rate = config.get('sample_rate', 60)  # 60Hz
        self.buffer_size = int(self.buffer_duration * self.sample_rate)
        
        # Time-series buffers
        self.telemetry_buffer = deque(maxlen=self.buffer_size)
        self.event_history = []
        
        # Session tracking
        self.session_data = {
            'type': 'practice',
            'lap_number': 0,
            'fuel_remaining_l': 0,
            'best_lap_time': float('inf'),
            'current_lap_time': 0.0
        }
        
        # Reference data (best laps, optimal values)
        self.reference_data = {}
        
        logger.info(f"Enhanced Context Builder initialized (buffer: {self.buffer_duration}s, {self.buffer_size} samples)")

    def add_telemetry(self, telemetry_data: Dict[str, Any]):
        """Add telemetry data to the time-series buffer"""
        try:
            # Create time-series point
            point = TimeSeriesPoint(
                timestamp=time.time(),
                steering_angle=telemetry_data.get('steering_angle', 0.0),
                brake=telemetry_data.get('brake_pct', 0.0) / 100.0,  # Convert to 0-1
                throttle=telemetry_data.get('throttle_pct', 0.0) / 100.0,  # Convert to 0-1
                gear=telemetry_data.get('gear', 0),
                speed_kph=telemetry_data.get('speed', 0.0) * 1.60934,  # Convert mph to kph
                rpm=telemetry_data.get('rpm', 0),
                slip_angle=self._calculate_slip_angle(telemetry_data),
                tire_temp=telemetry_data.get('tireTempLF', None),
                tire_pressure=telemetry_data.get('tirePressureLF', None)
            )
            
            self.telemetry_buffer.append(point)
            
            # Update session data
            self._update_session_data(telemetry_data)
            
        except Exception as e:
            logger.error(f"Error adding telemetry: {e}")

    def _calculate_slip_angle(self, telemetry_data: Dict[str, Any]) -> Optional[float]:
        """Calculate slip angle from telemetry data"""
        try:
            # Simplified slip angle calculation
            steering_angle = telemetry_data.get('steering_angle', 0.0)
            speed = telemetry_data.get('speed', 0.0)
            
            if speed > 0:
                # Basic slip angle approximation
                slip_angle = steering_angle * (speed / 100.0) * 0.1
                return round(slip_angle, 2)
        except Exception:
            pass
        return None

    def _update_session_data(self, telemetry_data: Dict[str, Any]):
        """Update session tracking data"""
        if 'lap' in telemetry_data:
            self.session_data['lap_number'] = telemetry_data['lap']
        
        if 'fuelLevel' in telemetry_data:
            self.session_data['fuel_remaining_l'] = telemetry_data['fuelLevel']
        
        if 'lapCurrentLapTime' in telemetry_data:
            self.session_data['current_lap_time'] = telemetry_data['lapCurrentLapTime']
        
        if 'lapBestLapTime' in telemetry_data:
            best_time = telemetry_data['lapBestLapTime']
            if best_time > 0 and best_time < self.session_data['best_lap_time']:
                self.session_data['best_lap_time'] = best_time

    def build_structured_context(self, 
                               event_type: str,
                               severity: str = "medium",
                               location: Optional[Dict[str, Any]] = None,
                               reference_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build structured JSON context for coaching advice.
        
        Args:
            event_type: Type of event (understeer, oversteer, etc.)
            severity: Event severity (low, medium, high)
            location: Track location information
            reference_data: Reference/optimal values for comparison
            
        Returns:
            Structured JSON context object
        """
        
        if not self.telemetry_buffer:
            logger.warning("No telemetry data available for context building")
            return self._create_empty_context(event_type, severity, location)
        
        # Get recent time-series data
        recent_data = list(self.telemetry_buffer)[-20:]  # Last 20 samples (~0.33s at 60Hz)
        
        # Extract time-series arrays
        driver_inputs = self._extract_driver_inputs(recent_data)
        car_state = self._extract_car_state(recent_data)
        tire_state = self._extract_tire_state(recent_data)
        
        # Build reference data
        reference = self._build_reference_data(reference_data, car_state)
        
        # Build event history
        history = self._build_event_history(event_type, severity)
        
        # Create structured context
        context = {
            "event": {
                "type": event_type,
                "severity": severity,
                "location": location or self._get_default_location(),
                "time": time.strftime("%H:%M:%S", time.localtime())
            },
            "driver_inputs": driver_inputs,
            "car_state": car_state,
            "tire_state": tire_state,
            "reference": reference,
            "history": history,
            "session": self.session_data.copy()
        }
        
        # Record event for history
        self._record_event(event_type, severity, location)
        
        return context

    def _extract_driver_inputs(self, data_points: List[TimeSeriesPoint]) -> Dict[str, List[float]]:
        """Extract driver input time-series data"""
        return {
            "steering_angle": [round(point.steering_angle, 2) for point in data_points],
            "brake": [round(point.brake, 3) for point in data_points],
            "throttle": [round(point.throttle, 3) for point in data_points],
            "gear": [point.gear for point in data_points]
        }

    def _extract_car_state(self, data_points: List[TimeSeriesPoint]) -> Dict[str, List[float]]:
        """Extract car state time-series data"""
        return {
            "speed_kph": [round(point.speed_kph, 1) for point in data_points],
            "rpm": [point.rpm for point in data_points],
            "slip_angle": [point.slip_angle for point in data_points if point.slip_angle is not None]
        }

    def _extract_tire_state(self, data_points: List[TimeSeriesPoint]) -> Dict[str, List[float]]:
        """Extract tire state time-series data"""
        temps = [point.tire_temp for point in data_points if point.tire_temp is not None]
        pressures = [point.tire_pressure for point in data_points if point.tire_pressure is not None]
        
        return {
            "temps": temps if temps else [],
            "pressures": pressures if pressures else []
        }

    def _build_reference_data(self, reference_data: Optional[Dict[str, Any]], 
                             car_state: Dict[str, List[float]]) -> Dict[str, Any]:
        """Build reference data for comparison"""
        reference = {}
        
        if reference_data:
            reference.update(reference_data)
        else:
            # Calculate basic reference values from current data
            if car_state.get('speed_kph'):
                speeds = car_state['speed_kph']
                reference['best_apex_speed'] = max(speeds) if speeds else 0
                reference['driver_apex_speed'] = min(speeds) if speeds else 0
                reference['sector_delta_s'] = 0.0  # Placeholder
        
        return reference

    def _build_event_history(self, current_event: str, current_severity: str) -> List[Dict[str, Any]]:
        """Build event history for pattern analysis"""
        history = []
        
        # Add current session events
        for event in self.event_history[-5:]:  # Last 5 events
            history.append({
                "lap": event.get('lap', self.session_data['lap_number']),
                "turn": event.get('turn', 'unknown'),
                "event": event.get('type', 'unknown'),
                "severity": event.get('severity', 'medium')
            })
        
        return history

    def _get_default_location(self) -> Dict[str, Any]:
        """Get default location information"""
        return {
            "track": "Unknown",
            "turn": "Unknown",
            "segment": "Unknown"
        }

    def _record_event(self, event_type: str, severity: str, location: Optional[Dict[str, Any]]):
        """Record event for history tracking"""
        event = {
            'type': event_type,
            'severity': severity,
            'lap': self.session_data['lap_number'],
            'timestamp': time.time()
        }
        
        if location:
            event.update(location)
        
        self.event_history.append(event)

    def _create_empty_context(self, event_type: str, severity: str, 
                            location: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create empty context when no telemetry data is available"""
        return {
            "event": {
                "type": event_type,
                "severity": severity,
                "location": location or self._get_default_location(),
                "time": time.strftime("%H:%M:%S", time.localtime())
            },
            "driver_inputs": {
                "steering_angle": [],
                "brake": [],
                "throttle": [],
                "gear": []
            },
            "car_state": {
                "speed_kph": [],
                "rpm": [],
                "slip_angle": []
            },
            "tire_state": {
                "temps": [],
                "pressures": []
            },
            "reference": {
                "best_apex_speed": 0,
                "driver_apex_speed": 0,
                "sector_delta_s": 0.0
            },
            "history": [],
            "session": self.session_data.copy()
        }

    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        return {
            "buffer_size": len(self.telemetry_buffer),
            "buffer_duration": self.buffer_duration,
            "sample_rate": self.sample_rate,
            "event_count": len(self.event_history),
            "session_lap": self.session_data['lap_number']
        }

    def clear_buffers(self):
        """Clear all buffers"""
        self.telemetry_buffer.clear()
        self.event_history.clear()
        logger.info("All buffers cleared")

    def export_context(self, context: Dict[str, Any], format: str = "json") -> str:
        """Export context in specified format"""
        if format.lower() == "json":
            return json.dumps(context, indent=2)
        elif format.lower() == "compact":
            return json.dumps(context, separators=(',', ':'))
        else:
            return str(context)

# Example usage and testing
def test_enhanced_context_builder():
    """Test the enhanced context builder"""
    logger.info("Testing Enhanced Context Builder...")
    
    # Initialize builder
    builder = EnhancedContextBuilder({
        'buffer_duration': 30.0,
        'sample_rate': 60
    })
    
    # Simulate telemetry data
    for i in range(10):
        telemetry = {
            'steering_angle': -5 + i * 0.5,
            'brake_pct': 30 + i * 2,
            'throttle_pct': 20 + i * 3,
            'gear': 3,
            'speed': 80 + i * 2,
            'rpm': 7000 + i * 100,
            'lap': 5,
            'fuelLevel': 25.0,
            'lapCurrentLapTime': 85.0 + i * 0.1
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
    
    # Export and display
    json_output = builder.export_context(context)
    logger.info(f"Generated context length: {len(json_output)} characters")
    
    return context

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_enhanced_context_builder() 