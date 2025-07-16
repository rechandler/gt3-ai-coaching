#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Machine Learning Coach
Provides real-time coaching using lightweight ML models and heuristics
"""

import numpy as np
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class PerformanceBaseline:
    """Baseline performance metrics for comparison"""
    best_lap_time: float = float('inf')
    best_sector_times: List[float] = field(default_factory=lambda: [float('inf')] * 3)
    optimal_speeds: Dict[str, float] = field(default_factory=dict)
    braking_points: Dict[str, float] = field(default_factory=dict)
    racing_line_deviation: float = 0.0

@dataclass
class DrivingPattern:
    """Represents a driving pattern or behavior"""
    name: str
    confidence: float
    severity: float
    frequency: int
    last_occurrence: float
    description: str

class TelemetryBuffer:
    """Rolling buffer for telemetry data analysis"""
    
    def __init__(self, max_size: int = 500):  # 50 seconds at 10Hz
        self.max_size = max_size
        self.data = deque(maxlen=max_size)
        self.timestamps = deque(maxlen=max_size)
    
    def add(self, telemetry: Dict[str, Any]):
        """Add telemetry data to buffer"""
        self.data.append(telemetry.copy())
        self.timestamps.append(time.time())
    
    def get_recent(self, seconds: float = 5.0) -> List[Dict[str, Any]]:
        """Get telemetry from the last N seconds"""
        cutoff_time = time.time() - seconds
        recent_data = []
        
        for i, timestamp in enumerate(self.timestamps):
            if timestamp >= cutoff_time:
                recent_data.append(self.data[i])
        
        return recent_data
    
    def get_range(self, start_idx: int, end_idx: int) -> List[Dict[str, Any]]:
        """Get telemetry data in a specific range"""
        return list(self.data)[start_idx:end_idx]

class PatternDetector:
    """Detects driving patterns and behaviors"""
    
    def __init__(self):
        self.patterns = {}
        self.thresholds = {
            'late_braking_threshold': 0.1,  # 100ms late
            'early_braking_threshold': 0.2,  # 200ms early
            'speed_threshold': 5.0,  # 5 km/h under optimal
            'line_deviation_threshold': 2.0,  # 2 meters off line
            'consistency_threshold': 0.05,  # 5% lap time variation
            'oversteer_steering_correction': 0.15,  # 15% steering reversal
            'understeer_high_angle': 0.18,  # 18% steering input (lowered)
            'understeer_low_yawrate': 0.08, # rad/s, low yaw rate (raised)
            'oversteer_high_yawrate': 0.15, # rad/s, high yaw rate
            'oversteer_countersteer': -0.1, # steering opposite to yaw
        }
    
    def detect_braking_patterns(self, recent_data: List[Dict[str, Any]]) -> List[DrivingPattern]:
        """Detect braking-related patterns"""
        patterns = []
        
        if len(recent_data) < 10:
            return patterns
        
        # Analyze braking points
        braking_events = []
        for i, data in enumerate(recent_data):
            if data.get('brake_pct', 0) > 10 and recent_data[i-1].get('brake_pct', 0) <= 10:
                braking_events.append({
                    'position': data.get('lap_distance_pct', 0),
                    'speed': data.get('speed', 0),
                    'brake_pressure': data.get('brake_pct', 0)
                })
        
        # Check for late braking pattern
        if len(braking_events) >= 2:
            avg_brake_pressure = np.mean([e['brake_pressure'] for e in braking_events])
            if avg_brake_pressure < 50:  # Less than 50% brake pressure
                patterns.append(DrivingPattern(
                    name="insufficient_braking",
                    confidence=0.8,
                    severity=0.6,
                    frequency=len(braking_events),
                    last_occurrence=time.time(),
                    description="Not using enough brake pressure"
                ))
        
        return patterns
    
    def detect_cornering_patterns(self, recent_data: List[Dict[str, Any]]) -> List[DrivingPattern]:
        """Detect cornering-related patterns, including robust oversteer/understeer"""
        import logging
        patterns = []
        if len(recent_data) < 20:
            return patterns
        # Find corners (where steering angle is significant)
        corners = []
        for i, data in enumerate(recent_data):
            steering = data.get('steering_angle', 0)
            abs_steering = abs(steering)
            yaw_rate = data.get('yawRate', 0)
            if abs_steering > 0.1:
                corners.append({
                    'steering': steering,
                    'abs_steering': abs_steering,
                    'yawRate': yaw_rate,
                    'speed': data.get('speed', 0),
                    'position': data.get('lap_distance_pct', 0),
                    'throttle': data.get('throttle_pct', 0)
                })
        # Robust Understeer: High steering angle, low yaw rate
        understeer_count = 0
        for c in corners:
            if c['abs_steering'] > self.thresholds['understeer_high_angle'] and abs(c['yawRate']) < self.thresholds['understeer_low_yawrate']:
                understeer_count += 1
        if understeer_count > 2:
            logging.debug(f"Understeer detected: count={understeer_count}, threshold={self.thresholds['understeer_high_angle']}, low_yawrate={self.thresholds['understeer_low_yawrate']}")
            patterns.append(DrivingPattern(
                name="understeer",
                confidence=0.85,
                severity=0.7,
                frequency=understeer_count,
                last_occurrence=time.time(),
                description="Robust understeer: high steering angle, low yaw rate"
            ))
        else:
            if understeer_count > 0:
                logging.debug(f"Near understeer: count={understeer_count}, threshold={self.thresholds['understeer_high_angle']}, low_yawrate={self.thresholds['understeer_low_yawrate']}")
        # Robust Oversteer: High yaw rate, steering input in opposite direction (countersteer)
        oversteer_count = 0
        for c in corners:
            # If yawRate and steering are in opposite directions and yawRate is high
            if c['yawRate'] * c['steering'] < self.thresholds['oversteer_countersteer'] and abs(c['yawRate']) > self.thresholds['oversteer_high_yawrate']:
                oversteer_count += 1
        if oversteer_count > 2:
            patterns.append(DrivingPattern(
                name="oversteer",
                confidence=0.8,
                severity=0.7,
                frequency=oversteer_count,
                last_occurrence=time.time(),
                description="Robust oversteer: high yaw rate, countersteering detected"
            ))
        # Existing early throttle detection
        if len(corners) >= 5:
            throttle_in_corners = [c['throttle'] for c in corners if c['abs_steering'] > 0.2]
            if throttle_in_corners and np.mean(throttle_in_corners) > 30:
                patterns.append(DrivingPattern(
                    name="early_throttle_in_corners",
                    confidence=0.7,
                    severity=0.5,
                    frequency=len(throttle_in_corners),
                    last_occurrence=time.time(),
                    description="Applying throttle too early while cornering"
                ))
        return patterns
    
    def detect_consistency_patterns(self, lap_times: List[float]) -> List[DrivingPattern]:
        """Detect consistency patterns"""
        patterns = []
        
        if len(lap_times) < 3:
            return patterns
        
        # Calculate lap time variation
        if len(lap_times) >= 3:
            lap_variation = np.std(lap_times[-5:]) / np.mean(lap_times[-5:])
            if lap_variation > self.thresholds['consistency_threshold']:
                patterns.append(DrivingPattern(
                    name="inconsistent_lap_times",
                    confidence=0.9,
                    severity=lap_variation * 2,  # Scale severity with variation
                    frequency=len(lap_times),
                    last_occurrence=time.time(),
                    description=f"Lap time variation: {lap_variation:.1%}"
                ))
        
        return patterns

class PerformanceAnalyzer:
    """Analyzes performance and suggests improvements"""
    
    def __init__(self):
        self.sector_times = defaultdict(list)
        self.speed_traps = defaultdict(list)
        self.baseline = PerformanceBaseline()
    
    def analyze_sector(self, sector: int, sector_time: float, 
                      telemetry_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sector performance"""
        self.sector_times[sector].append(sector_time)
        
        analysis = {
            'sector': sector,
            'time': sector_time,
            'improvement_potential': 0.0,
            'focus_areas': []
        }
        
        if len(self.sector_times[sector]) >= 3:
            best_time = min(self.sector_times[sector])
            current_vs_best = sector_time - best_time
            
            if current_vs_best > 0.1:  # More than 0.1s off best
                analysis['improvement_potential'] = current_vs_best
                
                # Analyze what went wrong
                if sector == 0:  # First sector - focus on start and braking
                    analysis['focus_areas'] = ['braking', 'racing_line']
                elif sector == 1:  # Middle sector - focus on cornering
                    analysis['focus_areas'] = ['cornering', 'throttle_application']
                else:  # Final sector - focus on exit speed
                    analysis['focus_areas'] = ['corner_exit', 'straight_line_speed']
        
        return analysis
    
    def analyze_speed_trap(self, position: float, speed: float) -> Dict[str, Any]:
        """Analyze speed trap performance"""
        self.speed_traps[position].append(speed)
        
        analysis = {
            'position': position,
            'speed': speed,
            'speed_deficit': 0.0,
            'suggestions': []
        }
        
        if len(self.speed_traps[position]) >= 3:
            best_speed = max(self.speed_traps[position])
            speed_deficit = best_speed - speed
            
            if speed_deficit > 2.0:  # More than 2 km/h deficit
                analysis['speed_deficit'] = speed_deficit
                analysis['suggestions'] = [
                    'Check corner exit technique',
                    'Optimize racing line for speed',
                    'Review gear selection'
                ]
        
        return analysis

class LocalMLCoach:
    """Main local ML coaching engine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.telemetry_buffer = TelemetryBuffer()
        self.pattern_detector = PatternDetector()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Coaching state
        self.current_lap = 0
        self.lap_times = []
        self.detected_patterns = {}
        self.coaching_tone = 'balanced'  # 'encouraging', 'critical', 'balanced'
        self.coaching_focus = 'all'  # 'consistency', 'speed', 'technique', 'all'
        
        # Load any existing ML models
        self.load_models()
        
        logger.info("Local ML Coach initialized")
    
    def load_models(self):
        """Load pre-trained models if available"""
        model_path = self.config.get('model_path', 'models/')
        if os.path.exists(model_path):
            # Load models here when implemented
            logger.info(f"Model path exists: {model_path}")
        else:
            logger.info("No pre-trained models found, using heuristic analysis")
    
    async def analyze(self, telemetry_data: Dict[str, Any], 
                     analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze telemetry and return coaching insights"""
        insights = []
        
        # Add to buffer
        self.telemetry_buffer.add(telemetry_data)
        
        # Get recent data for pattern analysis
        recent_data = self.telemetry_buffer.get_recent(5.0)
        # Detect patterns
        braking_patterns = self.pattern_detector.detect_braking_patterns(recent_data)
        cornering_patterns = self.pattern_detector.detect_cornering_patterns(recent_data)
        
        # Process patterns into insights
        for pattern in braking_patterns + cornering_patterns:
            insight = {
                'situation': pattern.name,
                'confidence': pattern.confidence,
                'importance': pattern.severity,
                'data': {
                    'pattern': pattern.name,
                    'frequency': pattern.frequency,
                    'description': pattern.description
                }
            }
            insights.append(insight)
        
        # Analyze sector performance if available
        if 'sector_time' in telemetry_data and 'sector' in telemetry_data:
            sector_analysis = self.performance_analyzer.analyze_sector(
                telemetry_data['sector'],
                telemetry_data['sector_time'],
                recent_data
            )
            
            if sector_analysis['improvement_potential'] > 0:
                insights.append({
                    'situation': 'sector_analysis',
                    'confidence': 0.8,
                    'importance': min(sector_analysis['improvement_potential'], 1.0),
                    'data': sector_analysis
                })
        
        # Check for lap completion
        if telemetry_data.get('lap_completed', False):
            lap_time = telemetry_data.get('last_lap_time', 0)
            if lap_time > 0:
                self.lap_times.append(lap_time)
                consistency_patterns = self.pattern_detector.detect_consistency_patterns(self.lap_times)
                
                for pattern in consistency_patterns:
                    insights.append({
                        'situation': pattern.name,
                        'confidence': pattern.confidence,
                        'importance': pattern.severity,
                        'data': {
                            'pattern': pattern.name,
                            'description': pattern.description
                        }
                    })
        return insights
    
    async def generate_message(self, insight: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a coaching message from an insight"""
        situation = insight['situation']
        confidence = insight['confidence']
        data = insight.get('data', {})
        
        # Generate message based on situation
        message = self.create_message_for_situation(situation, data, confidence)
        
        if message:
            return {
                'message': message,
                'category': self.categorize_situation(situation),
                'confidence': confidence
            }
        
        return None
    
    def create_message_for_situation(self, situation: str, data: Dict[str, Any], 
                                   confidence: float) -> Optional[str]:
        """Create a specific message for a situation"""
        
        messages = {
            'insufficient_braking': [
                "Try using more brake pressure - you're not maximizing your braking potential.",
                "You can brake harder! Use more of the brake pedal travel.",
                "Increase brake pressure to reduce your braking distances."
            ],
            'early_throttle_in_corners': [
                "Wait longer before applying throttle in corners for better balance.",
                "Focus on getting the car rotated before getting back on the throttle.",
                "Patience with throttle application will improve your corner exit speed."
            ],
            'inconsistent_lap_times': [
                "Focus on consistency - aim for repeatable lap times.",
                "Try to hit the same marks lap after lap for better consistency.",
                "Smooth inputs lead to consistent lap times."
            ],
            'sector_analysis': [
                f"You're losing time in sector {data.get('sector', 0)}. Focus on {', '.join(data.get('focus_areas', []))}.",
                f"Sector {data.get('sector', 0)} has {data.get('improvement_potential', 0):.2f}s of potential."
            ],
            # New: Oversteer/Understeer
            'oversteer': [
                "Watch out for oversteer! Try to be smoother with your steering corrections.",
                "You're experiencing oversteer in corners. Reduce throttle or unwind steering more gently.",
                "Oversteer detected: focus on balancing the car with smoother inputs."
            ],
            'understeer': [
                "Understeer detected: try slowing down more before turn-in.",
                "You're experiencing understeer. Reduce entry speed or use less steering angle.",
                "Understeer: focus on getting the car rotated before adding throttle."
            ]
        }
        
        # Select message based on tone
        if situation in messages:
            message_list = messages[situation]
            if self.coaching_tone == 'encouraging':
                # Pick more positive messages
                return message_list[0] if message_list else None
            else:
                # Pick appropriate message
                import random
                return random.choice(message_list) if message_list else None
        
        return None
    
    def categorize_situation(self, situation: str) -> str:
        """Categorize a situation for message filtering"""
        category_map = {
            'insufficient_braking': 'braking',
            'early_throttle_in_corners': 'throttle',
            'inconsistent_lap_times': 'consistency',
            'sector_analysis': 'performance'
        }
        
        return category_map.get(situation, 'general')
    
    def set_tone(self, tone: str):
        """Set coaching tone"""
        if tone in ['encouraging', 'critical', 'balanced']:
            self.coaching_tone = tone
            logger.info(f"Coaching tone set to: {tone}")
    
    def set_focus(self, focus: str):
        """Set coaching focus area"""
        if focus in ['consistency', 'speed', 'technique', 'all']:
            self.coaching_focus = focus
            logger.info(f"Coaching focus set to: {focus}")
    
    def set_mode(self, mode):
        """Set coaching mode"""
        # Adjust thresholds based on mode
        if mode.value == 'beginner':
            self.pattern_detector.thresholds['consistency_threshold'] = 0.1
        elif mode.value == 'advanced':
            self.pattern_detector.thresholds['consistency_threshold'] = 0.02
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coaching statistics"""
        return {
            'total_laps': len(self.lap_times),
            'patterns_detected': len(self.detected_patterns),
            'buffer_size': len(self.telemetry_buffer.data),
            'coaching_tone': self.coaching_tone,
            'coaching_focus': self.coaching_focus,
            'best_lap': min(self.lap_times) if self.lap_times else 0
        }

# Testing
async def test_local_coach():
    """Test the local ML coach"""
    config = {'model_path': 'models/'}
    coach = LocalMLCoach(config)
    
    # Simulate telemetry data
    test_telemetry = {
        'speed': 120,
        'brake_pct': 30,
        'throttle_pct': 0,
        'steering_angle': 0.2,
        'lap_distance_pct': 0.3,
        'sector': 1,
        'sector_time': 45.2
    }
    
    insights = await coach.analyze(test_telemetry, {})
    
    for insight in insights:
        message = await coach.generate_message(insight)
        if message:
            print(f"Coaching: {message['message']}")

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_local_coach())
