#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Micro Analysis System
=====================

Provides specific, actionable feedback with precise timing and speed deltas.
Implements the "braked 0.10s too late", "apex speed 3kph down" style analysis.
"""

import time
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class CornerReference:
    """Reference data for a specific corner"""
    corner_id: str
    corner_name: str
    track_name: str
    position_start: float
    position_end: float
    
    # Reference metrics (pro/best lap data)
    reference_brake_point: float  # Lap distance % where braking should start
    reference_brake_pressure: float  # Optimal brake pressure
    reference_entry_speed: float  # Speed entering corner
    reference_apex_speed: float  # Speed at apex
    reference_exit_speed: float  # Speed exiting corner
    reference_throttle_point: float  # Where throttle should be applied
    reference_throttle_pressure: float  # Optimal throttle pressure
    reference_steering_angle: float  # Optimal steering angle
    reference_racing_line: List[Tuple[float, float]]  # Position, steering pairs
    
    # Timing references
    reference_corner_time: float  # Expected time through corner
    reference_gear: int  # Optimal gear for corner
    
    # Additional context
    corner_type: str  # 'slow', 'medium', 'high_speed'
    difficulty: str  # 'easy', 'medium', 'hard'
    notes: str = ""

@dataclass
class MicroAnalysis:
    """Detailed micro-analysis results for a corner"""
    corner_id: str
    corner_name: str
    
    # Timing deltas (positive = late, negative = early)
    brake_timing_delta: float  # Seconds early/late
    throttle_timing_delta: float  # Seconds early/late
    
    # Speed deltas (positive = faster, negative = slower)
    entry_speed_delta: float  # km/h difference
    apex_speed_delta: float  # km/h difference
    exit_speed_delta: float  # km/h difference
    
    # Input deltas
    brake_pressure_delta: float  # Percentage difference
    throttle_pressure_delta: float  # Percentage difference
    steering_angle_delta: float  # Degrees difference
    
    # Racing line analysis
    racing_line_deviation: float  # Distance from optimal line
    line_smoothness_score: float  # 0-1, higher is smoother
    
    # Time loss analysis
    total_time_loss: float  # Seconds lost in corner
    time_loss_breakdown: Dict[str, float]  # Breakdown by factor
    
    # Pattern classification
    detected_patterns: List[str]  # e.g., "late_apex", "off_throttle_oversteer"
    pattern_confidence: Dict[str, float]  # Confidence scores for patterns
    
    # Specific feedback
    specific_feedback: List[str]  # Actionable advice
    priority: str  # 'critical', 'high', 'medium', 'low'

class ReferenceDataManager:
    """Manages reference data for corners and tracks"""
    
    def __init__(self, reference_file: str = "reference_data/corner_references.json"):
        self.reference_file = reference_file
        self.corner_references = {}
        self.load_references()
    
    def load_references(self):
        """Load corner reference data"""
        try:
            if os.path.exists(self.reference_file):
                with open(self.reference_file, 'r') as f:
                    data = json.load(f)
                    for corner_data in data.get('corners', []):
                        ref = CornerReference(**corner_data)
                        self.corner_references[ref.corner_id] = ref
                logger.info(f"📊 Loaded {len(self.corner_references)} corner references")
            else:
                logger.info("📊 No reference file found, will create from analysis")
        except Exception as e:
            logger.error(f"❌ Failed to load corner references: {e}")
    
    def save_references(self):
        """Save corner reference data"""
        try:
            os.makedirs(os.path.dirname(self.reference_file), exist_ok=True)
            data = {
                'corners': [
                    {
                        'corner_id': ref.corner_id,
                        'corner_name': ref.corner_name,
                        'track_name': ref.track_name,
                        'position_start': ref.position_start,
                        'position_end': ref.position_end,
                        'reference_brake_point': ref.reference_brake_point,
                        'reference_brake_pressure': ref.reference_brake_pressure,
                        'reference_entry_speed': ref.reference_entry_speed,
                        'reference_apex_speed': ref.reference_apex_speed,
                        'reference_exit_speed': ref.reference_exit_speed,
                        'reference_throttle_point': ref.reference_throttle_point,
                        'reference_throttle_pressure': ref.reference_throttle_pressure,
                        'reference_steering_angle': ref.reference_steering_angle,
                        'reference_racing_line': ref.reference_racing_line,
                        'reference_corner_time': ref.reference_corner_time,
                        'reference_gear': ref.reference_gear,
                        'corner_type': ref.corner_type,
                        'difficulty': ref.difficulty,
                        'notes': ref.notes
                    }
                    for ref in self.corner_references.values()
                ]
            }
            with open(self.reference_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Saved {len(self.corner_references)} corner references")
        except Exception as e:
            logger.error(f"❌ Failed to save corner references: {e}")
    
    def get_corner_reference(self, corner_id: str) -> Optional[CornerReference]:
        """Get reference data for a specific corner"""
        return self.corner_references.get(corner_id)
    
    def add_corner_reference(self, reference: CornerReference):
        """Add or update a corner reference"""
        self.corner_references[reference.corner_id] = reference
        self.save_references()
    
    def create_reference_from_best_lap(self, corner_id: str, corner_data: List[Dict]) -> CornerReference:
        """Create a reference from the best lap data"""
        if not corner_data:
            return None
        
        # Calculate reference metrics from best lap
        speeds = [d.get('speed', 0) for d in corner_data]
        brake_pressures = [d.get('brake', 0) for d in corner_data]
        throttle_pressures = [d.get('throttle', 0) for d in corner_data]
        steering_angles = [d.get('steering', 0) for d in corner_data]
        positions = [d.get('lap_distance_pct', 0) for d in corner_data]
        
        # Find key points
        brake_start_idx = next((i for i, b in enumerate(brake_pressures) if b > 10), 0)
        throttle_start_idx = next((i for i, t in enumerate(throttle_pressures) if t > 10), len(corner_data)-1)
        apex_idx = speeds.index(min(speeds)) if speeds else len(corner_data)//2
        
        reference = CornerReference(
            corner_id=corner_id,
            corner_name=corner_id.replace('_', ' ').title(),
            track_name="Unknown",
            position_start=positions[0] if positions else 0.0,
            position_end=positions[-1] if positions else 0.0,
            reference_brake_point=positions[brake_start_idx] if brake_start_idx < len(positions) else 0.0,
            reference_brake_pressure=max(brake_pressures) if brake_pressures else 0.0,
            reference_entry_speed=speeds[0] if speeds else 0.0,
            reference_apex_speed=speeds[apex_idx] if speeds and apex_idx < len(speeds) else 0.0,
            reference_exit_speed=speeds[-1] if speeds else 0.0,
            reference_throttle_point=positions[throttle_start_idx] if throttle_start_idx < len(positions) else 0.0,
            reference_throttle_pressure=max(throttle_pressures) if throttle_pressures else 0.0,
            reference_steering_angle=max(abs(s) for s in steering_angles) if steering_angles else 0.0,
            reference_racing_line=[(p, s) for p, s in zip(positions, steering_angles)],
            reference_corner_time=len(corner_data) / 60.0,  # Assuming 60Hz
            reference_gear=corner_data[len(corner_data)//2].get('gear', 3),
            corner_type='medium',
            difficulty='medium',
            notes="Generated from best lap data"
        )
        
        return reference

class PatternClassifier:
    """Classifies driving patterns using ML techniques"""
    
    def __init__(self):
        self.pattern_thresholds = {
            'late_apex': 0.1,  # 10% later than reference
            'early_apex': -0.1,  # 10% earlier than reference
            'off_throttle_oversteer': 0.3,  # High yaw rate with low throttle
            'understeer': 0.8,  # High steering with low yaw rate
            'trail_braking': 0.2,  # Brake pressure while steering
            'early_throttle': 0.15,  # Throttle before apex
            'late_throttle': -0.15,  # Throttle after apex
            'inconsistent_inputs': 0.25,  # High variance in inputs
        }
    
    def classify_patterns(self, corner_data: List[Dict], reference: CornerReference) -> Tuple[List[str], Dict[str, float]]:
        """Classify driving patterns in corner data"""
        patterns = []
        confidence = {}
        
        if not corner_data or not reference:
            return patterns, confidence
        
        # Extract key metrics
        speeds = [d.get('speed', 0) for d in corner_data]
        brake_pressures = [d.get('brake', 0) for d in corner_data]
        throttle_pressures = [d.get('throttle', 0) for d in corner_data]
        steering_angles = [d.get('steering', 0) for d in corner_data]
        yaw_rates = [d.get('yawRate', 0) for d in corner_data]
        positions = [d.get('lap_distance_pct', 0) for d in corner_data]
        
        # Find actual apex (minimum speed)
        actual_apex_idx = speeds.index(min(speeds)) if speeds else len(corner_data)//2
        actual_apex_pos = positions[actual_apex_idx] if actual_apex_idx < len(positions) else 0.5
        
        # Late/Early apex detection
        apex_timing_delta = (actual_apex_pos - reference.reference_throttle_point) / reference.reference_throttle_point
        if apex_timing_delta > self.pattern_thresholds['late_apex']:
            patterns.append('late_apex')
            confidence['late_apex'] = min(1.0, apex_timing_delta / 0.2)
        elif apex_timing_delta < self.pattern_thresholds['early_apex']:
            patterns.append('early_apex')
            confidence['early_apex'] = min(1.0, abs(apex_timing_delta) / 0.2)
        
        # Off-throttle oversteer detection
        for i, (throttle, yaw_rate) in enumerate(zip(throttle_pressures, yaw_rates)):
            if throttle < 20 and abs(yaw_rate) > self.pattern_thresholds['off_throttle_oversteer']:
                patterns.append('off_throttle_oversteer')
                confidence['off_throttle_oversteer'] = min(1.0, abs(yaw_rate) / 0.5)
                break
        
        # Understeer detection
        max_steering = max(abs(s) for s in steering_angles) if steering_angles else 0
        avg_yaw_rate = np.mean([abs(y) for y in yaw_rates]) if yaw_rates else 0
        if max_steering > self.pattern_thresholds['understeer'] and avg_yaw_rate < 0.1:
            patterns.append('understeer')
            confidence['understeer'] = min(1.0, max_steering / 1.0)
        
        # Trail braking detection
        brake_while_steering = 0
        for brake, steering in zip(brake_pressures, steering_angles):
            if brake > 20 and abs(steering) > 0.1:
                brake_while_steering += 1
        
        if brake_while_steering > len(corner_data) * 0.3:
            patterns.append('trail_braking')
            confidence['trail_braking'] = brake_while_steering / len(corner_data)
        
        # Early/Late throttle detection
        throttle_start_idx = next((i for i, t in enumerate(throttle_pressures) if t > 10), -1)
        if throttle_start_idx >= 0 and throttle_start_idx < len(positions):
            throttle_timing_delta = (positions[throttle_start_idx] - reference.reference_throttle_point) / reference.reference_throttle_point
            if throttle_timing_delta > self.pattern_thresholds['early_throttle']:
                patterns.append('early_throttle')
                confidence['early_throttle'] = min(1.0, throttle_timing_delta / 0.3)
            elif throttle_timing_delta < self.pattern_thresholds['late_throttle']:
                patterns.append('late_throttle')
                confidence['late_throttle'] = min(1.0, abs(throttle_timing_delta) / 0.3)
        
        # Inconsistent inputs detection
        throttle_variance = np.var(throttle_pressures) if len(throttle_pressures) > 1 else 0
        brake_variance = np.var(brake_pressures) if len(brake_pressures) > 1 else 0
        steering_variance = np.var(steering_angles) if len(steering_angles) > 1 else 0
        
        total_variance = (throttle_variance + brake_variance + steering_variance) / 3
        if total_variance > self.pattern_thresholds['inconsistent_inputs']:
            patterns.append('inconsistent_inputs')
            confidence['inconsistent_inputs'] = min(1.0, total_variance / 0.5)
        
        return patterns, confidence

class MicroAnalyzer:
    """Main micro-analysis engine"""
    
    def __init__(self, reference_manager: ReferenceDataManager = None):
        self.reference_manager = reference_manager or ReferenceDataManager()
        self.pattern_classifier = PatternClassifier()
        
        # Analysis state
        self.current_corner_data = []
        self.current_corner_id = None
        self.corner_start_position = None
        self.analysis_history = []
        
        logger.info("🔍 Micro Analyzer initialized")
    
    def start_corner_analysis(self, telemetry: Dict[str, Any], corner_id: str = None) -> bool:
        """Start analyzing a new corner"""
        steering_angle = abs(telemetry.get('steering', 0))
        lap_position = telemetry.get('lap_distance_pct', 0)
        
        # Detect corner entry (significant steering input)
        if steering_angle > 0.1 and not self.current_corner_id:
            self.current_corner_id = corner_id or f"corner_{lap_position:.2f}"
            self.corner_start_position = lap_position
            self.current_corner_data = [telemetry.copy()]
            logger.debug(f"🔄 Starting corner analysis: {self.current_corner_id}")
            return True
        
        return False
    
    def continue_corner_analysis(self, telemetry: Dict[str, Any]) -> bool:
        """Continue analyzing current corner"""
        if not self.current_corner_id:
            return False
        
        self.current_corner_data.append(telemetry.copy())
        
        # Check for corner exit (steering returns to near zero)
        steering_angle = abs(telemetry.get('steering', 0))
        if steering_angle < 0.05 and len(self.current_corner_data) > 5:
            return self.finalize_corner_analysis(telemetry)
        
        return True
    
    def finalize_corner_analysis(self, exit_telemetry: Dict[str, Any]) -> bool:
        """Finalize corner analysis and generate micro-analysis"""
        if not self.current_corner_id or not self.current_corner_data:
            return False
        
        try:
            # Get reference data
            reference = self.reference_manager.get_corner_reference(self.current_corner_id)
            
            # If no reference exists, create one from this data (assuming it's a good lap)
            if not reference:
                reference = self.reference_manager.create_reference_from_best_lap(
                    self.current_corner_id, self.current_corner_data
                )
                if reference:
                    self.reference_manager.add_corner_reference(reference)
                    logger.info(f"📊 Created reference for {self.current_corner_id}")
            
            # Perform micro-analysis
            analysis = self.perform_micro_analysis(self.current_corner_data, reference)
            
            # Store analysis
            self.analysis_history.append(analysis)
            
            # Log results
            logger.info(f"🎯 {self.current_corner_id}: {analysis.specific_feedback[0] if analysis.specific_feedback else 'Analysis complete'}")
            
            # Reset for next corner
            self.current_corner_id = None
            self.corner_start_position = None
            self.current_corner_data = []
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in corner analysis: {e}")
            return False
    
    def perform_micro_analysis(self, corner_data: List[Dict], reference: CornerReference) -> MicroAnalysis:
        """Perform detailed micro-analysis of corner performance"""
        
        # Extract key metrics
        speeds = [d.get('speed', 0) for d in corner_data]
        brake_pressures = [d.get('brake', 0) for d in corner_data]
        throttle_pressures = [d.get('throttle', 0) for d in corner_data]
        steering_angles = [d.get('steering', 0) for d in corner_data]
        positions = [d.get('lap_distance_pct', 0) for d in corner_data]
        
        # Find key points in actual data
        brake_start_idx = next((i for i, b in enumerate(brake_pressures) if b > 10), 0)
        throttle_start_idx = next((i for i, t in enumerate(throttle_pressures) if t > 10), len(corner_data)-1)
        apex_idx = speeds.index(min(speeds)) if speeds else len(corner_data)//2
        
        # Calculate timing deltas
        actual_brake_point = positions[brake_start_idx] if brake_start_idx < len(positions) else 0.0
        actual_throttle_point = positions[throttle_start_idx] if throttle_start_idx < len(positions) else 0.0
        
        # Convert position deltas to time deltas (rough approximation)
        brake_timing_delta = (actual_brake_point - reference.reference_brake_point) * 2.0  # 2s per 100% lap
        throttle_timing_delta = (actual_throttle_point - reference.reference_throttle_point) * 2.0
        
        # Calculate speed deltas
        entry_speed_delta = speeds[0] - reference.reference_entry_speed if speeds else 0.0
        apex_speed_delta = speeds[apex_idx] - reference.reference_apex_speed if speeds and apex_idx < len(speeds) else 0.0
        exit_speed_delta = speeds[-1] - reference.reference_exit_speed if speeds else 0.0
        
        # Calculate input deltas
        max_brake_pressure = max(brake_pressures) if brake_pressures else 0.0
        max_throttle_pressure = max(throttle_pressures) if throttle_pressures else 0.0
        max_steering_angle = max(abs(s) for s in steering_angles) if steering_angles else 0.0
        
        brake_pressure_delta = max_brake_pressure - reference.reference_brake_pressure
        throttle_pressure_delta = max_throttle_pressure - reference.reference_throttle_pressure
        steering_angle_delta = max_steering_angle - reference.reference_steering_angle
        
        # Calculate racing line deviation
        racing_line_deviation = self.calculate_racing_line_deviation(corner_data, reference)
        line_smoothness_score = self.calculate_line_smoothness(steering_angles)
        
        # Calculate time loss
        total_time_loss = self.calculate_time_loss(
            brake_timing_delta, throttle_timing_delta,
            entry_speed_delta, apex_speed_delta, exit_speed_delta
        )
        
        time_loss_breakdown = {
            'brake_timing': abs(brake_timing_delta) * 0.1,  # 0.1s per 0.1s timing error
            'throttle_timing': abs(throttle_timing_delta) * 0.1,
            'entry_speed': abs(entry_speed_delta) * 0.01,  # 0.01s per km/h
            'apex_speed': abs(apex_speed_delta) * 0.02,  # 0.02s per km/h (apex speed is critical)
            'exit_speed': abs(exit_speed_delta) * 0.01
        }
        
        # Classify patterns
        patterns, pattern_confidence = self.pattern_classifier.classify_patterns(corner_data, reference)
        
        # Generate specific feedback
        specific_feedback = self.generate_specific_feedback(
            brake_timing_delta, throttle_timing_delta,
            entry_speed_delta, apex_speed_delta, exit_speed_delta,
            brake_pressure_delta, throttle_pressure_delta, steering_angle_delta,
            patterns, total_time_loss
        )
        
        # Determine priority
        priority = self.determine_priority(total_time_loss, patterns, pattern_confidence)
        
        analysis = MicroAnalysis(
            corner_id=self.current_corner_id,
            corner_name=reference.corner_name if reference else self.current_corner_id,
            brake_timing_delta=brake_timing_delta,
            throttle_timing_delta=throttle_timing_delta,
            entry_speed_delta=entry_speed_delta,
            apex_speed_delta=apex_speed_delta,
            exit_speed_delta=exit_speed_delta,
            brake_pressure_delta=brake_pressure_delta,
            throttle_pressure_delta=throttle_pressure_delta,
            steering_angle_delta=steering_angle_delta,
            racing_line_deviation=racing_line_deviation,
            line_smoothness_score=line_smoothness_score,
            total_time_loss=total_time_loss,
            time_loss_breakdown=time_loss_breakdown,
            detected_patterns=patterns,
            pattern_confidence=pattern_confidence,
            specific_feedback=specific_feedback,
            priority=priority
        )
        
        return analysis
    
    def calculate_racing_line_deviation(self, corner_data: List[Dict], reference: CornerReference) -> float:
        """Calculate deviation from optimal racing line"""
        # Simplified calculation - could be more sophisticated
        steering_angles = [abs(d.get('steering', 0)) for d in corner_data]
        if not steering_angles:
            return 0.0
        
        # Compare to reference steering pattern
        if reference.reference_racing_line:
            # Calculate average deviation from reference line
            deviations = []
            for i, steering in enumerate(steering_angles):
                if i < len(reference.reference_racing_line):
                    ref_steering = abs(reference.reference_racing_line[i][1])
                    deviation = abs(steering - ref_steering)
                    deviations.append(deviation)
            
            return np.mean(deviations) if deviations else 0.0
        
        return 0.0
    
    def calculate_line_smoothness(self, steering_angles: List[float]) -> float:
        """Calculate smoothness of steering inputs (0-1, higher is smoother)"""
        if len(steering_angles) < 2:
            return 1.0
        
        # Calculate steering changes
        changes = []
        for i in range(1, len(steering_angles)):
            change = abs(steering_angles[i] - steering_angles[i-1])
            changes.append(change)
        
        # Smoothness is inverse of average change
        avg_change = np.mean(changes) if changes else 0.0
        smoothness = max(0.0, 1.0 - (avg_change / 0.5))  # Normalize to 0-1
        
        return smoothness
    
    def calculate_time_loss(self, brake_timing_delta: float, throttle_timing_delta: float,
                          entry_speed_delta: float, apex_speed_delta: float, exit_speed_delta: float) -> float:
        """Calculate total time loss in corner"""
        time_loss = 0.0
        
        # Timing errors
        time_loss += abs(brake_timing_delta) * 0.1  # 0.1s per 0.1s timing error
        time_loss += abs(throttle_timing_delta) * 0.1
        
        # Speed errors
        time_loss += abs(entry_speed_delta) * 0.01  # 0.01s per km/h
        time_loss += abs(apex_speed_delta) * 0.02   # 0.02s per km/h (apex speed is critical)
        time_loss += abs(exit_speed_delta) * 0.01   # 0.01s per km/h
        
        return time_loss
    
    def generate_specific_feedback(self, brake_timing_delta: float, throttle_timing_delta: float,
                                 entry_speed_delta: float, apex_speed_delta: float, exit_speed_delta: float,
                                 brake_pressure_delta: float, throttle_pressure_delta: float, steering_angle_delta: float,
                                 patterns: List[str], total_time_loss: float) -> List[str]:
        """Generate specific, actionable feedback"""
        feedback = []
        
        # Timing feedback
        if brake_timing_delta > 0.05:
            feedback.append(f"🛑 Braked {brake_timing_delta:.2f}s too late")
        elif brake_timing_delta < -0.05:
            feedback.append(f"🛑 Braked {abs(brake_timing_delta):.2f}s too early")
        
        if throttle_timing_delta > 0.05:
            feedback.append(f"🚀 Applied throttle {throttle_timing_delta:.2f}s too early")
        elif throttle_timing_delta < -0.05:
            feedback.append(f"🚀 Applied throttle {abs(throttle_timing_delta):.2f}s too late")
        
        # Speed feedback
        if apex_speed_delta < -2.0:
            feedback.append(f"⚡ Apex speed {abs(apex_speed_delta):.1f}km/h down")
        elif apex_speed_delta > 2.0:
            feedback.append(f"⚡ Apex speed {apex_speed_delta:.1f}km/h up (good!)")
        
        if entry_speed_delta < -5.0:
            feedback.append(f"🏁 Entry speed {abs(entry_speed_delta):.1f}km/h down")
        elif entry_speed_delta > 5.0:
            feedback.append(f"🏁 Entry speed {entry_speed_delta:.1f}km/h up (good!)")
        
        if exit_speed_delta < -3.0:
            feedback.append(f"🏁 Exit speed {abs(exit_speed_delta):.1f}km/h down")
        elif exit_speed_delta > 3.0:
            feedback.append(f"🏁 Exit speed {exit_speed_delta:.1f}km/h up (good!)")
        
        # Input feedback
        if brake_pressure_delta > 20:
            feedback.append(f"🛑 Brake pressure {brake_pressure_delta:.0f}% too high")
        elif brake_pressure_delta < -20:
            feedback.append(f"🛑 Brake pressure {abs(brake_pressure_delta):.0f}% too low")
        
        if throttle_pressure_delta > 30:
            feedback.append(f"🚀 Throttle pressure {throttle_pressure_delta:.0f}% too high")
        elif throttle_pressure_delta < -30:
            feedback.append(f"🚀 Throttle pressure {abs(throttle_pressure_delta):.0f}% too low")
        
        # Pattern feedback
        if 'late_apex' in patterns:
            feedback.append("🔄 Apex too late - turn in earlier")
        elif 'early_apex' in patterns:
            feedback.append("🔄 Apex too early - turn in later")
        
        if 'off_throttle_oversteer' in patterns:
            feedback.append("⚠️ Off-throttle oversteer detected - smoother inputs needed")
        
        if 'understeer' in patterns:
            feedback.append("⚠️ Understeer detected - reduce steering input")
        
        if 'trail_braking' in patterns:
            feedback.append("🛑 Trail braking detected - good technique!")
        
        if 'early_throttle' in patterns:
            feedback.append("🚀 Throttle too early - wait for apex")
        
        if 'late_throttle' in patterns:
            feedback.append("🚀 Throttle too late - apply earlier")
        
        if 'inconsistent_inputs' in patterns:
            feedback.append("📊 Inconsistent inputs - smooth out your driving")
        
        # Time loss summary
        if total_time_loss > 0.5:
            feedback.append(f"⏱️ Total time loss: {total_time_loss:.2f}s")
        elif total_time_loss < -0.2:
            feedback.append(f"⏱️ Time gained: {abs(total_time_loss):.2f}s (excellent!)")
        
        return feedback
    
    def determine_priority(self, total_time_loss: float, patterns: List[str], pattern_confidence: Dict[str, float]) -> str:
        """Determine priority of feedback"""
        # Critical patterns
        critical_patterns = ['off_throttle_oversteer', 'understeer']
        if any(p in patterns for p in critical_patterns):
            return 'critical'
        
        # High time loss
        if total_time_loss > 0.5:
            return 'high'
        
        # High confidence patterns
        if any(pattern_confidence.get(p, 0) > 0.8 for p in patterns):
            return 'high'
        
        # Medium time loss
        if total_time_loss > 0.2:
            return 'medium'
        
        return 'low'
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of recent analyses"""
        if not self.analysis_history:
            return {}
        
        recent_analyses = self.analysis_history[-10:]  # Last 10 analyses
        
        return {
            'total_analyses': len(self.analysis_history),
            'recent_analyses': len(recent_analyses),
            'average_time_loss': np.mean([a.total_time_loss for a in recent_analyses]),
            'most_common_patterns': self.get_most_common_patterns(recent_analyses),
            'improvement_trend': self.calculate_improvement_trend(recent_analyses)
        }
    
    def get_most_common_patterns(self, analyses: List[MicroAnalysis]) -> List[str]:
        """Get most common patterns from recent analyses"""
        pattern_counts = defaultdict(int)
        for analysis in analyses:
            for pattern in analysis.detected_patterns:
                pattern_counts[pattern] += 1
        
        # Return top 3 patterns
        return sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    def calculate_improvement_trend(self, analyses: List[MicroAnalysis]) -> str:
        """Calculate improvement trend"""
        if len(analyses) < 3:
            return "insufficient_data"
        
        recent_losses = [a.total_time_loss for a in analyses[-3:]]
        earlier_losses = [a.total_time_loss for a in analyses[-6:-3]] if len(analyses) >= 6 else recent_losses
        
        recent_avg = np.mean(recent_losses)
        earlier_avg = np.mean(earlier_losses)
        
        if recent_avg < earlier_avg * 0.8:
            return "improving"
        elif recent_avg > earlier_avg * 1.2:
            return "declining"
        else:
            return "stable"

# Testing
def test_micro_analyzer():
    """Test the micro analyzer"""
    analyzer = MicroAnalyzer()
    
    # Simulate corner data
    corner_data = [
        {'speed': 120, 'brake': 0, 'throttle': 80, 'steering': 0.0, 'lap_distance_pct': 0.25},
        {'speed': 100, 'brake': 60, 'throttle': 0, 'steering': 0.3, 'lap_distance_pct': 0.26},
        {'speed': 80, 'brake': 80, 'throttle': 0, 'steering': 0.5, 'lap_distance_pct': 0.27},
        {'speed': 70, 'brake': 40, 'throttle': 20, 'steering': 0.4, 'lap_distance_pct': 0.28},
        {'speed': 90, 'brake': 0, 'throttle': 60, 'steering': 0.2, 'lap_distance_pct': 0.29},
        {'speed': 110, 'brake': 0, 'throttle': 90, 'steering': 0.0, 'lap_distance_pct': 0.30}
    ]
    
    # Create reference
    reference = CornerReference(
        corner_id="test_corner",
        corner_name="Test Corner",
        track_name="Test Track",
        position_start=0.25,
        position_end=0.30,
        reference_brake_point=0.255,
        reference_brake_pressure=70,
        reference_entry_speed=120,
        reference_apex_speed=75,
        reference_exit_speed=115,
        reference_throttle_point=0.28,
        reference_throttle_pressure=80,
        reference_steering_angle=0.5,
        reference_racing_line=[(0.25, 0.0), (0.26, 0.3), (0.27, 0.5), (0.28, 0.4), (0.29, 0.2), (0.30, 0.0)],
        reference_corner_time=5.0,
        reference_gear=3,
        corner_type="medium",
        difficulty="medium"
    )
    
    # Perform analysis
    analysis = analyzer.perform_micro_analysis(corner_data, reference)
    
    print(f"Analysis: {analysis}")
    print(f"Feedback: {analysis.specific_feedback}")

if __name__ == "__main__":
    test_micro_analyzer() 