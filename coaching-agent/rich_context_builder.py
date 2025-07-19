#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rich Context Builder for GT3 AI Coaching
========================================

Implements the rich context structure for coaching prompts with comprehensive
multi-dimensional data to enable deeper AI insights and personalized coaching.
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
class EventContext:
    """Rich context for a driving event"""
    # Event identification
    event_type: str  # offtrack, oversteer, bad_exit, etc.
    event_timestamp: float
    event_location: str  # track segment/turn name
    
    # Car state at event
    car_state: Dict[str, Any] = field(default_factory=dict)
    
    # Track state
    track_state: Dict[str, Any] = field(default_factory=dict)
    
    # Tire & fuel state
    tire_fuel_state: Dict[str, Any] = field(default_factory=dict)
    
    # Driver input trace (window around event)
    driver_input_trace: List[Dict[str, Any]] = field(default_factory=list)
    
    # Lap/sector deltas
    lap_sector_deltas: Dict[str, Any] = field(default_factory=dict)
    
    # Session/trend history
    session_trends: Dict[str, Any] = field(default_factory=dict)
    
    # Setup baseline
    setup_baseline: Dict[str, Any] = field(default_factory=dict)
    
    # AI/ML anomaly scores
    anomaly_scores: Dict[str, float] = field(default_factory=dict)
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

class RichContextBuilder:
    """
    Builds rich context for coaching prompts with comprehensive multi-dimensional data.
    
    Key Data Dimensions:
    - Event type: offtrack, oversteer, bad exit, etc.
    - Car state: speed, revs, gear, throttle/brake/steering traces
    - Track state: name, segment, entry/exit data, weather
    - Tire & fuel state: temps, pressures, wear, fuel remaining
    - Driver input trace: a window around the event
    - Lap/sector deltas: vs. best lap, reference lap, ideal values
    - Session/trend history: Has this event happened repeatedly? Getting better/worse?
    - Setup baseline (if available): camber, toe, tire psi, etc.
    - AI/ML anomaly scores: Deviation from model-predicted "ideal" driver inputs
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Telemetry buffer for input traces
        self.telemetry_buffer = deque(maxlen=300)  # 5 seconds at 60Hz
        
        # Session history tracking
        self.session_events = defaultdict(list)
        self.event_patterns = defaultdict(int)
        
        # Performance baselines
        self.best_lap_time = float('inf')
        self.reference_lap_time = float('inf')
        self.sector_baselines = {}
        
        # Setup tracking
        self.current_setup = {}
        
        # Anomaly detection
        self.ideal_patterns = {}
        
        logger.info("Rich Context Builder initialized")
    
    def add_telemetry(self, telemetry_data: Dict[str, Any]):
        """Add telemetry data to the buffer for input traces"""
        self.telemetry_buffer.append({
            'timestamp': time.time(),
            'data': telemetry_data.copy()
        })
    
    def build_rich_context(self, 
                          event_type: str,
                          telemetry_data: Dict[str, Any],
                          context: Any,
                          current_segment: Optional[Dict[str, Any]] = None,
                          event_window_seconds: float = 2.0) -> EventContext:
        """
        Build comprehensive rich context for a coaching event.
        
        Args:
            event_type: Type of event (offtrack, oversteer, bad_exit, etc.)
            telemetry_data: Current telemetry data
            context: Coaching context object
            current_segment: Current track segment info
            event_window_seconds: Time window around event for input trace
            
        Returns:
            EventContext with all rich context dimensions
        """
        
        # Build car state
        car_state = self._build_car_state(telemetry_data)
        
        # Build track state
        track_state = self._build_track_state(telemetry_data, context, current_segment)
        
        # Build tire & fuel state
        tire_fuel_state = self._build_tire_fuel_state(telemetry_data)
        
        # Build driver input trace
        driver_input_trace = self._build_driver_input_trace(
            telemetry_data, event_window_seconds
        )
        
        # Build lap/sector deltas
        lap_sector_deltas = self._build_lap_sector_deltas(telemetry_data)
        
        # Build session/trend history
        session_trends = self._build_session_trends(event_type, telemetry_data)
        
        # Build setup baseline
        setup_baseline = self._build_setup_baseline(telemetry_data)
        
        # Build anomaly scores
        anomaly_scores = self._build_anomaly_scores(telemetry_data, event_type)
        
        # Create event context
        event_context = EventContext(
            event_type=event_type,
            event_timestamp=time.time(),
            event_location=current_segment.get('name', 'Unknown') if current_segment else 'Unknown',
            car_state=car_state,
            track_state=track_state,
            tire_fuel_state=tire_fuel_state,
            driver_input_trace=driver_input_trace,
            lap_sector_deltas=lap_sector_deltas,
            session_trends=session_trends,
            setup_baseline=setup_baseline,
            anomaly_scores=anomaly_scores,
            metadata={
                'context_version': '1.0',
                'builder_timestamp': time.time()
            }
        )
        
        # Record event for trend analysis
        self._record_event(event_type, event_context)
        
        return event_context

    def build_structured_context(self, 
                               event_type: str,
                               telemetry_data: Dict[str, Any],
                               context: Any,
                               current_segment: Optional[Dict[str, Any]] = None,
                               severity: str = "medium") -> Dict[str, Any]:
        """
        Build structured JSON context using the enhanced approach.
        
        Args:
            event_type: Type of event (understeer, oversteer, etc.)
            telemetry_data: Current telemetry data
            context: Coaching context object
            current_segment: Current track segment info
            severity: Event severity (low, medium, high)
            
        Returns:
            Structured JSON context object
        """
        
        # Add telemetry to buffer
        self.add_telemetry(telemetry_data)
        
        # Determine location
        location = self._get_default_location()
        if current_segment:
            location = {
                "track": getattr(context, 'track_name', 'Unknown'),
                "turn": current_segment.get('name', 'Unknown'),
                "segment": current_segment.get('type', 'Unknown')
            }
        
        # Build reference data
        reference_data = self._build_reference_data_for_structured(telemetry_data, context)
        
        # Create structured context
        structured_context = {
            "event": {
                "type": event_type,
                "severity": severity,
                "location": location,
                "time": time.strftime("%H:%M:%S", time.localtime())
            },
            "driver_inputs": self._extract_driver_inputs_structured(),
            "car_state": self._extract_car_state_structured(),
            "tire_state": self._extract_tire_state_structured(),
            "reference": reference_data,
            "history": self._build_event_history_structured(event_type, severity),
            "session": self._build_session_data_structured(context)
        }
        
        # Record event for history
        self._record_structured_event(event_type, severity, location)
        
        return structured_context

    def _extract_driver_inputs_structured(self) -> Dict[str, List[float]]:
        """Extract driver inputs in structured format"""
        if not self.telemetry_buffer:
            return {"steering_angle": [], "brake": [], "throttle": [], "gear": []}
        
        # Get recent data points
        recent_data = list(self.telemetry_buffer)[-20:]  # Last 20 samples
        
        return {
            "steering_angle": [round(data['data'].get('steering_angle', 0), 2) for data in recent_data],
            "brake": [round(data['data'].get('brake_pct', 0) / 100.0, 3) for data in recent_data],
            "throttle": [round(data['data'].get('throttle_pct', 0) / 100.0, 3) for data in recent_data],
            "gear": [data['data'].get('gear', 0) for data in recent_data]
        }

    def _extract_car_state_structured(self) -> Dict[str, List[float]]:
        """Extract car state in structured format"""
        if not self.telemetry_buffer:
            return {"speed_kph": [], "rpm": [], "slip_angle": []}
        
        recent_data = list(self.telemetry_buffer)[-20:]
        
        slip_angles = [self._calculate_slip_angle(data['data']) for data in recent_data]
        slip_angles = [angle for angle in slip_angles if angle is not None]
        
        return {
            "speed_kph": [round(data['data'].get('speed', 0) * 1.60934, 1) for data in recent_data],
            "rpm": [data['data'].get('rpm', 0) for data in recent_data],
            "slip_angle": slip_angles
        }

    def _extract_tire_state_structured(self) -> Dict[str, List[float]]:
        """Extract tire state in structured format"""
        if not self.telemetry_buffer:
            return {"temps": [], "pressures": []}
        
        recent_data = list(self.telemetry_buffer)[-20:]
        
        temps = [data['data'].get('tireTempLF') for data in recent_data if data['data'].get('tireTempLF') is not None]
        pressures = [data['data'].get('tirePressureLF') for data in recent_data if data['data'].get('tirePressureLF') is not None]
        
        return {
            "temps": temps,
            "pressures": pressures
        }

    def _calculate_slip_angle(self, telemetry_data: Dict[str, Any]) -> Optional[float]:
        """Calculate slip angle from telemetry data"""
        try:
            steering_angle = telemetry_data.get('steering_angle', 0.0)
            speed = telemetry_data.get('speed', 0.0)
            
            if speed > 0:
                slip_angle = steering_angle * (speed / 100.0) * 0.1
                return round(slip_angle, 2)
        except Exception:
            pass
        return None

    def _build_reference_data_for_structured(self, telemetry_data: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Build reference data for structured context"""
        current_speed = telemetry_data.get('speed', 0) * 1.60934  # Convert to kph
        
        return {
            "best_apex_speed": current_speed * 1.1,  # 10% higher as reference
            "driver_apex_speed": current_speed,
            "sector_delta_s": telemetry_data.get('lapDeltaToBestLap', 0.0)
        }

    def _build_event_history_structured(self, current_event: str, current_severity: str) -> List[Dict[str, Any]]:
        """Build event history for structured context"""
        history = []
        
        # Add recent events from session
        for event_type, events in self.session_events.items():
            for event in events[-3:]:  # Last 3 events per type
                history.append({
                    "lap": event.get('lap', 0),
                    "turn": event.get('location', 'Unknown'),
                    "event": event_type,
                    "severity": "medium"  # Default severity
                })
        
        return history

    def _build_session_data_structured(self, context: Any) -> Dict[str, Any]:
        """Build session data for structured context"""
        return {
            "type": getattr(context, 'session_type', 'practice'),
            "lap_number": getattr(context, 'lap_count', 0),
            "fuel_remaining_l": 25.0,  # Placeholder
            "best_lap_time": getattr(context, 'best_lap_time', 0.0),
            "current_lap_time": 0.0  # Would need to track this
        }

    def _get_default_location(self) -> Dict[str, Any]:
        """Get default location information"""
        return {
            "track": "Unknown",
            "turn": "Unknown",
            "segment": "Unknown"
        }

    def _record_structured_event(self, event_type: str, severity: str, location: Optional[Dict[str, Any]]):
        """Record event for structured history tracking"""
        # This would integrate with the existing event recording system
        pass
    
    def _build_car_state(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive car state information"""
        return {
            'speed': telemetry_data.get('speed', 0),
            'rpm': telemetry_data.get('rpm', 0),
            'gear': telemetry_data.get('gear', 0),
            'throttle_pct': telemetry_data.get('throttle_pct', 0),
            'brake_pct': telemetry_data.get('brake_pct', 0),
            'steering_angle': telemetry_data.get('steering_angle', 0),
            'steering_torque': telemetry_data.get('steering_torque', 0),
            'acceleration': {
                'longitudinal': telemetry_data.get('longAccel', 0),
                'lateral': telemetry_data.get('latAccel', 0),
                'vertical': telemetry_data.get('vertAccel', 0)
            },
            'velocity': {
                'x': telemetry_data.get('velocityX', 0),
                'y': telemetry_data.get('velocityY', 0),
                'z': telemetry_data.get('velocityZ', 0)
            },
            'orientation': {
                'yaw': telemetry_data.get('yaw', 0),
                'pitch': telemetry_data.get('pitch', 0),
                'roll': telemetry_data.get('roll', 0)
            },
            'surface': telemetry_data.get('playerTrackSurface', 'Unknown')
        }
    
    def _build_track_state(self, telemetry_data: Dict[str, Any], 
                          context: Any, current_segment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build track state information"""
        track_state = {
            'name': getattr(context, 'track_name', 'Unknown'),
            'lap_distance_pct': telemetry_data.get('lap_distance_pct', 0),
            'lap_number': telemetry_data.get('lap', 0),
            'session_type': getattr(context, 'session_type', 'Practice'),
            'weather': {
                'air_temp': telemetry_data.get('airTemp', 0),
                'track_temp': telemetry_data.get('trackTempCrew', 0),
                'weather_type': telemetry_data.get('weatherType', 'Unknown')
            }
        }
        
        # Add segment information if available
        if current_segment:
            track_state['current_segment'] = {
                'name': current_segment.get('name', 'Unknown'),
                'type': current_segment.get('type', 'Unknown'),
                'description': current_segment.get('description', ''),
                'start_pct': current_segment.get('start_pct', 0),
                'end_pct': current_segment.get('end_pct', 0)
            }
        
        return track_state
    
    def _build_tire_fuel_state(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build tire and fuel state information"""
        return {
            'tire_pressures': {
                'front_left': telemetry_data.get('tirePressureLF', 0),
                'front_right': telemetry_data.get('tirePressureRF', 0),
                'rear_left': telemetry_data.get('tirePressureLR', 0),
                'rear_right': telemetry_data.get('tirePressureRR', 0)
            },
            'tire_temperatures': {
                'front_left': telemetry_data.get('tireTempLF', 0),
                'front_right': telemetry_data.get('tireTempRF', 0),
                'rear_left': telemetry_data.get('tireTempLR', 0),
                'rear_right': telemetry_data.get('tireTempRR', 0)
            },
            'tire_wear': {
                'front_left': telemetry_data.get('tireWearLF', 0),
                'front_right': telemetry_data.get('tireWearRF', 0),
                'rear_left': telemetry_data.get('tireWearLR', 0),
                'rear_right': telemetry_data.get('tireWearRR', 0)
            },
            'fuel': {
                'level': telemetry_data.get('fuelLevel', 0),
                'level_pct': telemetry_data.get('fuelLevelPct', 0),
                'use_per_hour': telemetry_data.get('fuelUsePerHour', 0)
            }
        }
    
    def _build_driver_input_trace(self, telemetry_data: Dict[str, Any], 
                                 window_seconds: float) -> List[Dict[str, Any]]:
        """Build driver input trace around the event"""
        current_time = time.time()
        trace_start = current_time - window_seconds
        
        # Filter telemetry buffer for the time window
        trace_data = []
        for entry in self.telemetry_buffer:
            if entry['timestamp'] >= trace_start:
                trace_data.append({
                    'timestamp': entry['timestamp'],
                    'relative_time': entry['timestamp'] - current_time,
                    'speed': entry['data'].get('speed', 0),
                    'throttle_pct': entry['data'].get('throttle_pct', 0),
                    'brake_pct': entry['data'].get('brake_pct', 0),
                    'steering_angle': entry['data'].get('steering_angle', 0),
                    'gear': entry['data'].get('gear', 0),
                    'rpm': entry['data'].get('rpm', 0),
                    'lap_distance_pct': entry['data'].get('lap_distance_pct', 0)
                })
        
        return trace_data
    
    def _build_lap_sector_deltas(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build lap and sector delta information"""
        current_lap_time = telemetry_data.get('lapCurrentLapTime', 0)
        best_lap_time = telemetry_data.get('lapBestLapTime', 0)
        session_best_lap = telemetry_data.get('lapDeltaToSessionBestLap', 0)
        
        # Calculate deltas
        delta_to_best = current_lap_time - best_lap_time if best_lap_time > 0 else 0
        delta_to_session_best = session_best_lap if session_best_lap != 999 else 0
        
        return {
            'current_lap_time': current_lap_time,
            'best_lap_time': best_lap_time,
            'delta_to_best': delta_to_best,
            'delta_to_session_best': delta_to_session_best,
            'sector_times': telemetry_data.get('sector_times', []),
            'sector_deltas': telemetry_data.get('sector_deltas', []),
            'improvement_potential': max(0, delta_to_best) if delta_to_best > 0 else 0
        }
    
    def _build_session_trends(self, event_type: str, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build session and trend history"""
        # Get event history for this session
        session_events = self.session_events[event_type]
        
        # Calculate trends
        event_count = len(session_events)
        recent_events = [e for e in session_events if time.time() - e['timestamp'] < 300]  # Last 5 minutes
        
        # Determine trend direction
        trend_direction = 'stable'
        if len(recent_events) > 3:
            if len(recent_events) > len(session_events) * 0.7:  # 70% of events in last 5 min
                trend_direction = 'worsening'
            elif len(recent_events) < len(session_events) * 0.3:  # 30% of events in last 5 min
                trend_direction = 'improving'
        
        return {
            'event_type': event_type,
            'total_occurrences': event_count,
            'recent_occurrences': len(recent_events),
            'trend_direction': trend_direction,
            'frequency_per_lap': event_count / max(1, telemetry_data.get('lap', 1)),
            'last_occurrence': session_events[-1]['timestamp'] if session_events else 0,
            'pattern_analysis': self._analyze_event_pattern(event_type)
        }
    
    def _build_setup_baseline(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build setup baseline information"""
        return {
            'tire_pressures': {
                'front_left': telemetry_data.get('tirePressureLF', 0),
                'front_right': telemetry_data.get('tirePressureRF', 0),
                'rear_left': telemetry_data.get('tirePressureLR', 0),
                'rear_right': telemetry_data.get('tirePressureRR', 0)
            },
            'suspension': {
                'front_ride_height': telemetry_data.get('frontRideHeight', 0),
                'rear_ride_height': telemetry_data.get('rearRideHeight', 0),
                'front_spring_rate': telemetry_data.get('frontSpringRate', 0),
                'rear_spring_rate': telemetry_data.get('rearSpringRate', 0)
            },
            'alignment': {
                'front_camber': telemetry_data.get('frontCamber', 0),
                'rear_camber': telemetry_data.get('rearCamber', 0),
                'front_toe': telemetry_data.get('frontToe', 0),
                'rear_toe': telemetry_data.get('rearToe', 0)
            },
            'differential': {
                'preload': telemetry_data.get('diffPreload', 0),
                'power_setting': telemetry_data.get('diffPowerSetting', 0),
                'coast_setting': telemetry_data.get('diffCoastSetting', 0)
            }
        }
    
    def _build_anomaly_scores(self, telemetry_data: Dict[str, Any], event_type: str) -> Dict[str, float]:
        """Build AI/ML anomaly scores"""
        scores = {}
        
        # Calculate deviation from ideal patterns
        if event_type in self.ideal_patterns:
            ideal = self.ideal_patterns[event_type]
            current = {
                'speed': telemetry_data.get('speed', 0),
                'throttle': telemetry_data.get('throttle_pct', 0),
                'brake': telemetry_data.get('brake_pct', 0),
                'steering': telemetry_data.get('steering_angle', 0)
            }
            
            # Calculate deviation scores (0-1, where 1 is maximum deviation)
            for key in current:
                if key in ideal:
                    deviation = abs(current[key] - ideal[key]) / max(1, ideal[key])
                    scores[f'{key}_deviation'] = min(1.0, deviation)
        
        # Add general anomaly scores
        scores['overall_anomaly'] = self._calculate_overall_anomaly(telemetry_data)
        scores['technique_anomaly'] = self._calculate_technique_anomaly(telemetry_data)
        
        return scores
    
    def _calculate_overall_anomaly(self, telemetry_data: Dict[str, Any]) -> float:
        """Calculate overall anomaly score"""
        # Simple heuristic-based anomaly detection
        speed = telemetry_data.get('speed', 0)
        throttle = telemetry_data.get('throttle_pct', 0)
        brake = telemetry_data.get('brake_pct', 0)
        steering = abs(telemetry_data.get('steering_angle', 0))
        
        # Anomaly indicators
        anomalies = []
        
        # High throttle + high brake
        if throttle > 50 and brake > 20:
            anomalies.append(0.8)
        
        # High speed + high steering
        if speed > 150 and steering > 0.5:
            anomalies.append(0.6)
        
        # Low speed + high throttle
        if speed < 50 and throttle > 80:
            anomalies.append(0.4)
        
        return max(anomalies) if anomalies else 0.0
    
    def _calculate_technique_anomaly(self, telemetry_data: Dict[str, Any]) -> float:
        """Calculate technique-specific anomaly score"""
        # Technique-based anomaly detection
        speed = telemetry_data.get('speed', 0)
        throttle = telemetry_data.get('throttle_pct', 0)
        brake = telemetry_data.get('brake_pct', 0)
        steering = abs(telemetry_data.get('steering_angle', 0))
        
        # Corner entry technique anomalies
        if steering > 0.3:  # In a corner
            if brake < 10 and speed > 100:  # High speed, no brake
                return 0.7
            if throttle > 50 and brake > 30:  # Throttle while braking
                return 0.6
        
        # Straight line anomalies
        if steering < 0.1:  # On straight
            if brake > 20 and speed > 100:  # Braking on straight
                return 0.5
        
        return 0.0
    
    def _record_event(self, event_type: str, event_context: EventContext):
        """Record event for trend analysis"""
        self.session_events[event_type].append({
            'timestamp': event_context.event_timestamp,
            'location': event_context.event_location,
            'car_state': event_context.car_state.copy(),
            'anomaly_scores': event_context.anomaly_scores.copy()
        })
        
        # Update event pattern count
        self.event_patterns[event_type] += 1
    
    def _analyze_event_pattern(self, event_type: str) -> Dict[str, Any]:
        """Analyze patterns in event occurrences"""
        events = self.session_events[event_type]
        
        if len(events) < 2:
            return {'pattern': 'insufficient_data'}
        
        # Analyze timing patterns
        timestamps = [e['timestamp'] for e in events]
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        min_interval = min(intervals) if intervals else 0
        max_interval = max(intervals) if intervals else 0
        
        return {
            'pattern': 'recurring' if len(events) > 2 else 'occasional',
            'frequency': {
                'average_interval': avg_interval,
                'min_interval': min_interval,
                'max_interval': max_interval
            },
            'locations': list(set(e['location'] for e in events)),
            'severity_trend': self._calculate_severity_trend(events)
        }
    
    def _calculate_severity_trend(self, events: List[Dict[str, Any]]) -> str:
        """Calculate severity trend of events"""
        if len(events) < 3:
            return 'insufficient_data'
        
        # Use anomaly scores as severity indicator
        recent_anomalies = [e['anomaly_scores'].get('overall_anomaly', 0) for e in events[-3:]]
        earlier_anomalies = [e['anomaly_scores'].get('overall_anomaly', 0) for e in events[:-3]]
        
        if not earlier_anomalies:
            return 'stable'
        
        recent_avg = sum(recent_anomalies) / len(recent_anomalies)
        earlier_avg = sum(earlier_anomalies) / len(earlier_anomalies)
        
        if recent_avg > earlier_avg * 1.2:
            return 'worsening'
        elif recent_avg < earlier_avg * 0.8:
            return 'improving'
        else:
            return 'stable'
    
    def format_for_prompt(self, event_context: EventContext) -> str:
        """
        Format rich context for inclusion in coaching prompts.
        
        Returns a structured string representation of the rich context
        that can be included in LLM prompts.
        """
        context_str = f"""
=== RICH CONTEXT FOR COACHING ===

EVENT: {event_context.event_type.upper()}
Location: {event_context.event_location}
Timestamp: {event_context.event_timestamp}

CAR STATE:
- Speed: {event_context.car_state.get('speed', 0):.1f} mph
- RPM: {event_context.car_state.get('rpm', 0):.0f}
- Gear: {event_context.car_state.get('gear', 0)}
- Throttle: {event_context.car_state.get('throttle_pct', 0):.1f}%
- Brake: {event_context.car_state.get('brake_pct', 0):.1f}%
- Steering: {event_context.car_state.get('steering_angle', 0):.3f}
- Surface: {event_context.car_state.get('surface', 'Unknown')}

TRACK STATE:
- Track: {event_context.track_state.get('name', 'Unknown')}
- Lap Distance: {event_context.track_state.get('lap_distance_pct', 0):.1%}
- Lap: {event_context.track_state.get('lap_number', 0)}
- Session: {event_context.track_state.get('session_type', 'Unknown')}
- Weather: {event_context.track_state.get('weather', {}).get('weather_type', 'Unknown')}

TIRE & FUEL STATE:
- Tire Pressures: FL={event_context.tire_fuel_state.get('tire_pressures', {}).get('front_left', 0):.1f}, FR={event_context.tire_fuel_state.get('tire_pressures', {}).get('front_right', 0):.1f}, RL={event_context.tire_fuel_state.get('tire_pressures', {}).get('rear_left', 0):.1f}, RR={event_context.tire_fuel_state.get('tire_pressures', {}).get('rear_right', 0):.1f}
- Fuel Level: {event_context.tire_fuel_state.get('fuel', {}).get('level_pct', 0):.1f}%

LAP/SECTOR DELTAS:
- Current Lap: {event_context.lap_sector_deltas.get('current_lap_time', 0):.3f}s
- Best Lap: {event_context.lap_sector_deltas.get('best_lap_time', 0):.3f}s
- Delta to Best: {event_context.lap_sector_deltas.get('delta_to_best', 0):.3f}s
- Improvement Potential: {event_context.lap_sector_deltas.get('improvement_potential', 0):.3f}s

SESSION TRENDS:
- Event Type: {event_context.session_trends.get('event_type', 'Unknown')}
- Total Occurrences: {event_context.session_trends.get('total_occurrences', 0)}
- Recent Occurrences: {event_context.session_trends.get('recent_occurrences', 0)}
- Trend Direction: {event_context.session_trends.get('trend_direction', 'Unknown')}
- Frequency per Lap: {event_context.session_trends.get('frequency_per_lap', 0):.2f}

ANOMALY SCORES:
- Overall Anomaly: {event_context.anomaly_scores.get('overall_anomaly', 0):.3f}
- Technique Anomaly: {event_context.anomaly_scores.get('technique_anomaly', 0):.3f}

DRIVER INPUT TRACE (Last {len(event_context.driver_input_trace)} samples):
"""
        
        # Add driver input trace (last 5 samples)
        trace_samples = event_context.driver_input_trace[-5:]
        for i, sample in enumerate(trace_samples):
            context_str += f"- T{i}: Speed={sample.get('speed', 0):.1f}, Throttle={sample.get('throttle_pct', 0):.1f}%, Brake={sample.get('brake_pct', 0):.1f}%, Steering={sample.get('steering_angle', 0):.3f}\n"
        
        context_str += "\n=== END RICH CONTEXT ===\n"
        
        return context_str
    
    def get_context_summary(self, event_context: EventContext) -> Dict[str, Any]:
        """Get a summary of the rich context for logging/debugging"""
        return {
            'event_type': event_context.event_type,
            'location': event_context.event_location,
            'timestamp': event_context.event_timestamp,
            'car_state_summary': {
                'speed': event_context.car_state.get('speed', 0),
                'throttle': event_context.car_state.get('throttle_pct', 0),
                'brake': event_context.car_state.get('brake_pct', 0),
                'steering': event_context.car_state.get('steering_angle', 0)
            },
            'track_state_summary': {
                'track': event_context.track_state.get('name', 'Unknown'),
                'lap_distance': event_context.track_state.get('lap_distance_pct', 0)
            },
            'session_trends_summary': {
                'total_occurrences': event_context.session_trends.get('total_occurrences', 0),
                'trend_direction': event_context.session_trends.get('trend_direction', 'Unknown')
            },
            'anomaly_scores_summary': {
                'overall': event_context.anomaly_scores.get('overall_anomaly', 0),
                'technique': event_context.anomaly_scores.get('technique_anomaly', 0)
            }
        } 