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
            'understeer_high_angle': 0.25,  # 25% steering input (increased from 0.18)
            'understeer_low_yawrate': 0.05, # rad/s, low yaw rate (decreased from 0.08)
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
            # Only detect understeer in actual cornering situations (not on straights)
            if (c['abs_steering'] > self.thresholds['understeer_high_angle'] and 
                abs(c['yawRate']) < self.thresholds['understeer_low_yawrate'] and
                c['speed'] > 50):  # Only detect at higher speeds
                understeer_count += 1
        if understeer_count > 5:  # Increased from 2 to 5
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
            lap_variation = float(np.std(lap_times[-5:])) / float(np.mean(lap_times[-5:]))
            if lap_variation > self.thresholds['consistency_threshold']:
                patterns.append(DrivingPattern(
                    name="inconsistent_lap_times",
                    confidence=0.9,
                    severity=float(lap_variation * 2),  # Scale severity with variation
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
        
        # Message deduplication
        self.recent_messages = {}  # Track recent messages by category
        self.message_cooldown = 8.0  # Seconds before same message can be sent again
        self.combined_messages = {}  # Track combined messages by category
        
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
    
    def _should_send_message(self, situation: str, category: str) -> bool:
        """Check if a message should be sent based on cooldown and deduplication"""
        current_time = time.time()
        
        # Special cooldown for understeer/oversteer messages
        if situation in ['understeer', 'oversteer']:
            cooldown = 15.0  # 15 seconds for car balance issues
        else:
            cooldown = self.message_cooldown
        
        # Check if we have a recent message of this type
        if category in self.recent_messages:
            last_time = self.recent_messages[category].get('timestamp', 0)
            if current_time - last_time < cooldown:
                logger.debug(f"Skipping {situation} message for {category} - cooldown active ({cooldown}s)")
                return False
        
        logger.debug(f"Allowing {situation} message for {category}")
        return True
    
    def _combine_similar_messages(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine similar insights into comprehensive messages"""
        if not insights:
            return []
        
        # Group insights by category
        grouped_insights = {}
        for insight in insights:
            category = self.categorize_situation(insight.get('situation', 'general'))
            if category not in grouped_insights:
                grouped_insights[category] = []
            grouped_insights[category].append(insight)
        
        # Combine similar insights
        combined_insights = []
        current_time = time.time()
        
        for category, category_insights in grouped_insights.items():
            if len(category_insights) == 1:
                # Single insight, keep as is
                combined_insights.append(category_insights[0])
                logger.debug(f"Single {category} insight: {category_insights[0].get('situation')}")
            else:
                # Multiple similar insights, combine them
                logger.info(f"Combining {len(category_insights)} {category} insights into single message")
                combined_insight = self._create_combined_insight(category_insights, category)
                if combined_insight:
                    combined_insights.append(combined_insight)
                    
                    # Track the combined message
                    self.combined_messages[category] = {
                        'timestamp': current_time,
                        'count': len(category_insights),
                        'insights': category_insights
                    }
        
        return combined_insights
    
    def _create_combined_insight(self, insights: List[Dict[str, Any]], category: str) -> Dict[str, Any]:
        """Create a combined insight from multiple similar insights"""
        if not insights:
            return None
        
        # Use the highest confidence and importance
        max_confidence = max(insight.get('confidence', 0) for insight in insights)
        max_importance = max(insight.get('importance', 0) for insight in insights)
        
        # Create comprehensive description
        descriptions = [insight.get('data', {}).get('description', '') for insight in insights]
        combined_description = f"Multiple {category} issues detected: " + "; ".join(descriptions)
        
        # Create combined insight
        combined_insight = {
            'situation': f'combined_{category}',
            'confidence': max_confidence,
            'importance': max_importance,
            'data': {
                'pattern': f'combined_{category}',
                'frequency': len(insights),
                'description': combined_description,
                'combined_insights': insights
            }
        }
        
        return combined_insight
    
    async def analyze(self, telemetry_data: Dict[str, Any], 
                     analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze telemetry and return coaching insights with reference comparisons"""
        insights = []
        
        # Add to buffer
        self.telemetry_buffer.add(telemetry_data)
        
        # Get recent data for pattern analysis
        recent_data = self.telemetry_buffer.get_recent(5.0)
        
        # Get reference context for professional coaching
        reference_context = analysis.get('reference_context', {})
        
        # Detect patterns
        braking_patterns = self.pattern_detector.detect_braking_patterns(recent_data)
        cornering_patterns = self.pattern_detector.detect_cornering_patterns(recent_data)
        
        logger.debug(f"Detected patterns: {len(braking_patterns)} braking, {len(cornering_patterns)} cornering")
        
        # Process patterns into insights with reference comparisons
        for pattern in braking_patterns + cornering_patterns:
            category = self.categorize_situation(pattern.name)
            
            # Check if we should send this message
            if not self._should_send_message(pattern.name, category):
                logger.debug(f"Skipping {pattern.name} due to cooldown")
                continue
            
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
            
            # Add reference context if available
            if reference_context.get('reference_available'):
                insight['reference_context'] = reference_context
                insight['data'].update({
                    'reference_type': reference_context.get('reference_type'),
                    'delta_to_reference': reference_context.get('delta_to_reference', 0.0),
                    'improvement_potential': reference_context.get('improvement_potential', 0.0)
                })
                
                # Add reference speed comparisons
                reference_speeds = reference_context.get('reference_speeds', {})
                if reference_speeds:
                    current_speed = telemetry_data.get('speed', 0)
                    reference_entry = reference_speeds.get('entry_speed', 0)
                    reference_exit = reference_speeds.get('exit_speed', 0)
                    
                    if current_speed < reference_entry * 0.9:
                        insight['data']['speed_deficit'] = f"Entry speed {current_speed:.1f} vs reference {reference_entry:.1f}"
                    if current_speed < reference_exit * 0.9:
                        insight['data']['exit_deficit'] = f"Exit speed {current_speed:.1f} vs reference {reference_exit:.1f}"
            
            # Add driver_issue for understeer/oversteer
            if pattern.name == 'understeer':
                insight['data']['driver_issue'] = 'experiencing understeer'
            elif pattern.name == 'oversteer':
                insight['data']['driver_issue'] = 'experiencing oversteer'
            
            insights.append(insight)
            logger.info(f"Generated insight: {pattern.name} (confidence={pattern.confidence:.2f}, severity={pattern.severity:.2f})")
            
            # Track this message
            self.recent_messages[category] = {
                'timestamp': time.time(),
                'situation': pattern.name,
                'confidence': pattern.confidence
            }
        
        # Analyze sector performance if available
        if 'sector_time' in telemetry_data and 'sector' in telemetry_data:
            sector_analysis = self.performance_analyzer.analyze_sector(
                telemetry_data['sector'],
                telemetry_data['sector_time'],
                recent_data
            )
            
            if sector_analysis['improvement_potential'] > 0:
                sector_insight = {
                    'situation': 'sector_analysis',
                    'confidence': 0.8,
                    'importance': min(sector_analysis['improvement_potential'], 1.0),
                    'data': sector_analysis
                }
                
                # Add reference context to sector analysis
                if reference_context.get('reference_available'):
                    sector_insight['reference_context'] = reference_context
                
                insights.append(sector_insight)
                logger.info(f"Generated sector insight: sector {telemetry_data['sector']}")
        
        # Check for lap completion
        if telemetry_data.get('lap_completed', False):
            lap_time = telemetry_data.get('last_lap_time', 0)
            if lap_time > 0:
                self.lap_times.append(lap_time)
                consistency_patterns = self.pattern_detector.detect_consistency_patterns(self.lap_times)
                
                for pattern in consistency_patterns:
                    consistency_insight = {
                        'situation': pattern.name,
                        'confidence': pattern.confidence,
                        'importance': pattern.severity,
                        'data': {
                            'pattern': pattern.name,
                            'description': pattern.description
                        }
                    }
                    
                    # Add reference context to consistency analysis
                    if reference_context.get('reference_available'):
                        consistency_insight['reference_context'] = reference_context
                    
                    insights.append(consistency_insight)
                    logger.info(f"Generated consistency insight: {pattern.name}")
        
        # Combine similar insights before returning
        combined_insights = self._combine_similar_messages(insights)
        
        logger.info(f"Returning {len(combined_insights)} insights (from {len(insights)} original)")
        
        return combined_insights
    
    async def generate_message(self, insight: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a coaching message from an insight"""
        # Handle different insight structures
        if 'situation' in insight:
            # Original format
            situation = insight['situation']
        elif 'type' in insight and 'category' in insight:
            # New format from hybrid coach
            insight_type = insight['type']
            category = insight['category']
            
            # Map insight type and category to situation
            if insight_type == 'micro_analysis':
                if 'brake' in category.lower() or 'braking' in category.lower():
                    situation = 'insufficient_braking'
                elif 'throttle' in category.lower():
                    situation = 'early_throttle_in_corners'
                elif 'consistency' in category.lower():
                    situation = 'inconsistent_lap_times'
                elif 'performance' in category.lower():
                    situation = 'sector_analysis'
                else:
                    situation = 'general'
            elif insight_type == 'enhanced_context':
                if 'braking_technique' in category:
                    situation = 'insufficient_braking'
                elif 'consistency' in category:
                    situation = 'inconsistent_lap_times'
                elif 'speed_management' in category:
                    situation = 'sector_analysis'
                else:
                    situation = 'general'
            else:
                situation = 'general'
        else:
            # Fallback
            situation = 'general'
        
        confidence = insight.get('confidence', 0.5)
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
        """Create a specific message for a situation with reference comparisons"""
        
        # Check for reference context
        reference_context = data.get('reference_context', {})
        has_reference = reference_context.get('reference_available', False)
        
        # Handle combined messages
        if situation.startswith('combined_'):
            category = situation.replace('combined_', '')
            return self._create_combined_message(category, data, confidence)
        
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
            ],
            'general': [
                "Focus on smooth, consistent inputs for better lap times.",
                "Keep working on your technique - consistency is key.",
                "Stay focused on the fundamentals of good driving."
            ]
        }
        
        # Add reference-specific messages if available
        if has_reference:
            reference_type = reference_context.get('reference_type', 'reference')
            delta = reference_context.get('delta_to_reference', 0.0)
            improvement = reference_context.get('improvement_potential', 0.0)
            
            # Add reference-based messages
            if situation == 'insufficient_braking':
                messages['insufficient_braking'].extend([
                    f"Compared to your {reference_type}: you're {delta:.2f}s slower. Focus on brake technique.",
                    f"Your {reference_type} shows {improvement:.2f}s of improvement potential in braking zones."
                ])
            elif situation == 'early_throttle_in_corners':
                messages['early_throttle_in_corners'].extend([
                    f"Your {reference_type} shows better throttle timing. You're {delta:.2f}s slower in corners.",
                    f"Focus on corner exit technique - your {reference_type} shows {improvement:.2f}s of potential."
                ])
            elif situation == 'sector_analysis':
                messages['sector_analysis'].extend([
                    f"Your {reference_type} shows {improvement:.2f}s of improvement potential in this sector.",
                    f"Delta to {reference_type}: {delta:.2f}s. Focus on the key areas identified."
                ])
            
            # Add speed deficit messages
            if 'speed_deficit' in data:
                messages[situation].append(f"Speed deficit: {data['speed_deficit']}")
            if 'exit_deficit' in data:
                messages[situation].append(f"Exit speed issue: {data['exit_deficit']}")
        
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
    
    def _create_combined_message(self, category: str, data: Dict[str, Any], confidence: float) -> str:
        """Create a comprehensive message for combined insights"""
        combined_insights = data.get('combined_insights', [])
        frequency = data.get('frequency', 1)
        
        if category == 'car_balance':
            if frequency >= 3:
                return "Multiple car balance issues detected: Focus on entry speed, steering angle, and throttle timing for better cornering."
            elif frequency >= 2:
                return "Car balance needs work: Reduce entry speed and be more patient with throttle application."
            else:
                return "Car balance issue: Adjust your entry speed or steering technique."
        
        elif category == 'braking':
            if frequency >= 3:
                return "Multiple braking issues: Focus on brake timing and pressure for better corner entry."
            elif frequency >= 2:
                return "Braking technique needs improvement: Work on timing and pressure."
            else:
                return "Braking issue detected: Adjust your brake technique."
        
        elif category == 'throttle':
            if frequency >= 3:
                return "Multiple throttle issues: Be more patient with throttle application for better corner exits."
            elif frequency >= 2:
                return "Throttle timing needs work: Wait longer before applying throttle."
            else:
                return "Throttle issue: Adjust your throttle timing."
        
        else:
            # Generic combined message
            descriptions = [insight.get('data', {}).get('description', '') for insight in combined_insights]
            return f"Multiple {category} issues: " + "; ".join(descriptions)
    
    def categorize_situation(self, situation: str) -> str:
        """Categorize a situation for message filtering"""
        category_map = {
            'insufficient_braking': 'braking',
            'early_throttle_in_corners': 'throttle',
            'inconsistent_lap_times': 'consistency',
            'sector_analysis': 'performance',
            'oversteer': 'car_balance',
            'understeer': 'car_balance',
            'general': 'general'
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

    def predict(self, driver_inputs, car_state, tire_state, reference, session):
        """
        Predict expected/optimal driver input profiles and flag anomalies.
        Returns a dict suitable for 'ml_analysis' in the advice context.
        """
        # Example: Compare actual vs. reference, flag anomalies
        ml_analysis = {
            'anomaly_score': 0.0,
            'anomaly_type': None,
            'expected_profile': {},
            'deviation': {},
            'significant': False
        }
        # Example: Check for late braking (brake applied later than expected)
        if 'brake' in driver_inputs and 'brake' in reference:
            actual_brake = driver_inputs['brake']
            expected_brake = reference.get('brake', actual_brake)
            if len(actual_brake) > 0 and len(expected_brake) > 0:
                # Simple anomaly: mean brake timing difference
                brake_diff = sum(actual_brake) / len(actual_brake) - sum(expected_brake) / len(expected_brake)
                ml_analysis['deviation']['brake_timing'] = f"{brake_diff:+.2f}s"
                if brake_diff > 0.1:
                    ml_analysis['anomaly_type'] = 'late_brake'
                    ml_analysis['anomaly_score'] = min(abs(brake_diff), 1.0)
                    ml_analysis['significant'] = True
        # Example: Compare apex speed
        if 'speed_kph' in car_state and 'best_apex_speed' in reference:
            actual_apex = min(car_state['speed_kph']) if car_state['speed_kph'] else 0
            optimal_apex = reference['best_apex_speed']
            speed_deficit = optimal_apex - actual_apex
            ml_analysis['deviation']['apex_speed_deficit'] = speed_deficit
            if speed_deficit > 5:
                ml_analysis['anomaly_type'] = 'low_apex_speed'
                ml_analysis['anomaly_score'] = min(speed_deficit / 10, 1.0)
                ml_analysis['significant'] = True
        # Add expected profile (could be from a real ML model)
        ml_analysis['expected_profile'] = {
            'brake': reference.get('brake', []),
            'throttle': reference.get('throttle', []),
            'speed_kph': [reference.get('best_apex_speed', 0)]
        }
        return ml_analysis

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
