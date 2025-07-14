#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified Local AI Coaching Engine for GT3 Racing
Provides real-time driving analysis and coaching feedback with session persistence
"""

import numpy as np
import time
import logging
import sys
import io
import random
import requests
import json
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict
from dataclasses import dataclass, field

# Try to import LLM config, fall back to defaults
try:
    from llm_config import LLM_ENABLED, OPENAI_API_KEY, LLM_MODEL, LLM_COOLDOWN, TRACK_SECTIONS
except ImportError:
    LLM_ENABLED = False
    OPENAI_API_KEY = "your-openai-api-key-here"
    LLM_MODEL = "gpt-3.5-turbo"
    LLM_COOLDOWN = 10.0
    TRACK_SECTIONS = {
        0.0: "Start/Finish Straight", 0.1: "Turn 1", 0.2: "First Complex",
        0.3: "Back Straight", 0.4: "Turn 2", 0.5: "Chicane",
        0.6: "Fast Corners", 0.7: "Tight Corners", 0.8: "Final Sector", 0.9: "Last Corner"
    }

# Import session persistence
from session_persistence import SessionPersistenceManager, SessionData

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logger = logging.getLogger(__name__)

@dataclass
class LapData:
    """Stores data for a single lap"""
    lap_number: int
    lap_time: float
    sectors: List[float] = field(default_factory=list)
    max_speed: float = 0.0
    avg_speed: float = 0.0
    timestamp: float = field(default_factory=time.time)

@dataclass
class CoachingMessage:
    """A coaching message with metadata"""
    message: str
    category: str  # 'braking', 'throttle', 'tires', 'racing_line', 'general'
    priority: int  # 1-10, higher = more important
    confidence: float  # 0-100, how confident the AI is
    data_source: str  # what telemetry triggered this
    improvement_potential: float = 0.0  # estimated lap time improvement in seconds

class LocalAICoach:
    """Simplified Local AI coaching system with session persistence"""
    
    def __init__(self, data_dir: str = "coaching_data", cloud_sync_enabled: bool = False):
        # Session persistence
        self.persistence_manager = SessionPersistenceManager(data_dir, cloud_sync_enabled)
        self.current_session: Optional[SessionData] = None
        self.track_name = "unknown"
        self.car_name = "unknown"
        
        # Lap data (reduced memory usage)
        self.laps: List[LapData] = []
        self.current_lap_data = {}
        self.best_lap: Optional[LapData] = None
        self.baseline_established = False
        self.baseline_just_established = False
        self.session_start_time = time.time()
        
        # AI Learning Parameters (simplified)
        self.consistency_threshold = 0.05
        self.driving_style = "unknown"
        self.coaching_intensity = 1.0
        
        # Reduced telemetry buffer (30 seconds instead of 60)
        self.telemetry_buffer = deque(maxlen=1800)  # 30 seconds at 60Hz
        
        # Simplified corner analysis
        self.corner_analysis = defaultdict(lambda: {
            'brake_points': deque(maxlen=5),  # Only keep last 5
            'entry_speeds': deque(maxlen=5),
            'exit_speeds': deque(maxlen=5)
        })
        
        # Message deduplication
        self.recent_messages = {}
        self.message_cooldown = 3.0
        
        # LLM Integration
        self.llm_enabled = LLM_ENABLED
        self.llm_api_key = OPENAI_API_KEY
        self.llm_model = LLM_MODEL
        self.llm_cooldown = LLM_COOLDOWN
        self.last_llm_message = 0
        
        # Store track section mapping for LLM context
        self.track_sections = TRACK_SECTIONS
        
        logger.info("🤖 AI Coach initialized with session persistence")
    
    def start_session(self, track_name: str, car_name: str, load_previous: bool = True) -> bool:
        """Start a new session, optionally loading previous data"""
        self.track_name = track_name
        self.car_name = car_name
        
        # Try to load previous baseline if requested
        if load_previous:
            baseline = self.persistence_manager.get_track_baseline(track_name, car_name)
            if baseline:
                self.baseline_established = True
                self.driving_style = baseline.get('driving_style', 'unknown')
                self.consistency_threshold = baseline.get('consistency_threshold', 0.05)
                self.coaching_intensity = baseline.get('coaching_intensity', 1.0)
                
                # Load corner analysis
                corner_data = baseline.get('corner_analysis', {})
                for corner, data in corner_data.items():
                    self.corner_analysis[corner].update(data)
                
                logger.info(f"📊 Loaded baseline for {track_name} + {car_name}")
                logger.info(f"   Style: {self.driving_style}, Consistency: {self.consistency_threshold:.1%}")
        
        # Create new session
        self.current_session = self.persistence_manager.create_session(track_name, car_name)
        
        return True
    
    def reset_baseline(self) -> bool:
        """Reset baseline for current track/car combination"""
        if not self.track_name or not self.car_name:
            return False
        
        success = self.persistence_manager.reset_baseline(self.track_name, self.car_name)
        if success:
            self.baseline_established = False
            self.driving_style = "unknown"
            self.consistency_threshold = 0.05
            self.coaching_intensity = 1.0
            self.corner_analysis.clear()
            logger.info("🔄 Baseline reset - will re-establish after 3 laps")
        
        return success
    
    def process_telemetry(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Process incoming telemetry and generate coaching messages - ALL through LLM with comprehensive analysis"""
        try:
            # Add to telemetry buffer
            telemetry['timestamp'] = time.time()
            self.telemetry_buffer.append(telemetry.copy())
            
            # Update current lap data
            self._update_current_lap_data(telemetry)
            
            # Generate coaching messages
            messages = []
            
            # Log comprehensive analysis status every 10 seconds
            current_time = time.time()
            if not hasattr(self, '_last_analysis_log_time'):
                self._last_analysis_log_time = 0
            
            if current_time - self._last_analysis_log_time > 10.0:
                speed = telemetry.get('Speed', 0)  # Capital S for iRacing field
                throttle = telemetry.get('Throttle', 0)  # Capital T for iRacing field  
                brake = telemetry.get('Brake', 0)  # Capital B for iRacing field
                steering = telemetry.get('SteeringWheelAngle', 0)  # Correct iRacing field name
                delta_time = telemetry.get('LapDeltaToSessionBestLap', 0)  # Correct iRacing field name
                
                logger.info(f"🔍 COMPREHENSIVE DRIVING ANALYSIS ACTIVE")
                logger.info(f"📊 Current State: Speed={speed:.1f}mph, Throttle={throttle:.1f}%, Brake={brake:.1f}%, Steering={steering:.1f}°")
                logger.info(f"⏱️  Performance: Delta={delta_time:.2f}s, Track={telemetry.get('TrackDisplayName', 'Unknown')}")  # Correct iRacing field name
                logger.info(f"🎯 Analyzing: Braking, Throttle, Steering, Racing Line, Speed Management, Technique, Strategy")
                self._last_analysis_log_time = current_time
            
            # If baseline not established, only show countdown message (non-LLM)
            if not self.baseline_established:
                countdown_message = self._generate_baseline_countdown(telemetry)
                if countdown_message:
                    messages.append(countdown_message)
                return self._prioritize_messages(messages)
            
            # *** ALL COACHING MESSAGES NOW GO THROUGH LLM WITH COMPREHENSIVE ANALYSIS ***
            # Detect ALL possible coaching situations and let LLM handle them
            coaching_situations = self._detect_all_coaching_situations(telemetry)
            
            for situation in coaching_situations:
                llm_message = self._generate_llm_coaching_for_situation(telemetry, situation)
                if llm_message:
                    messages.append(llm_message)
                    logger.info(f"✅ Generated coaching for situation: {situation}")
            
            return self._prioritize_messages(messages)
            
        except Exception as e:
            logger.error(f"Error in AI coaching: {e}")
            return [CoachingMessage(
                message="AI Coach temporarily unavailable",
                category="general",
                priority=1,
                confidence=100,
                data_source="system"
            )]
    
    def _update_current_lap_data(self, telemetry: Dict[str, Any]):
        """Update current lap data collection"""
        lap_num = telemetry.get('lap', 0)
        
        # Check if we completed a lap
        if hasattr(self, '_last_lap_num') and lap_num > self._last_lap_num:
            self._complete_lap()
        
        self._last_lap_num = lap_num
        
        # Update current lap metrics
        self.current_lap_data.update({
            'lap_number': lap_num,
            'current_lap_time': telemetry.get('lapCurrentLapTime', 0),
            'speed': telemetry.get('speed', 0),
            'throttle': telemetry.get('throttle', 0),
            'brake': telemetry.get('brake', 0),
        })
    
    def _complete_lap(self):
        """Process completed lap and update AI models"""
        if not self.current_lap_data:
            return
        
        try:
            lap_time = self.current_lap_data.get('current_lap_time', 0)
            if lap_time <= 0:
                return
            
            lap = LapData(
                lap_number=self.current_lap_data.get('lap_number', 0),
                lap_time=lap_time
            )
            
            self.laps.append(lap)
            
            # Update best lap
            if not self.best_lap or lap_time < self.best_lap.lap_time:
                self.best_lap = lap
                logger.info(f"🏆 New best lap: {lap_time:.3f}s (Lap {lap.lap_number})")
            
            # Establish baseline after 3 laps
            if len(self.laps) >= 3 and not self.baseline_established:
                self._establish_baseline()
                self.baseline_established = True
                self.baseline_just_established = True
                logger.info("📊 AI baseline established")
            
            # Save session data periodically
            if self.current_session and len(self.laps) % 5 == 0:  # Every 5 laps
                self._save_session_data()
            
        except Exception as e:
            logger.error(f"Error completing lap: {e}")
    
    def _establish_baseline(self):
        """Establish performance baseline from first few laps"""
        if len(self.laps) < 3:
            return
        
        lap_times = [lap.lap_time for lap in self.laps if lap.lap_time > 0]
        if lap_times:
            avg_lap_time = np.mean(lap_times)
            std_lap_time = np.std(lap_times)
            self.consistency_threshold = max(0.02, min(0.1, std_lap_time / avg_lap_time))
            logger.info(f"📈 Baseline: Avg lap {avg_lap_time:.3f}s")
    
    def _save_session_data(self):
        """Save current session data to persistence"""
        if not self.current_session:
            return
        
        try:
            # Update session with current data
            self.current_session.laps = [
                {
                    'lap_number': lap.lap_number,
                    'lap_time': lap.lap_time,
                    'timestamp': lap.timestamp
                } for lap in self.laps
            ]
            
            if self.best_lap:
                self.current_session.best_lap_time = self.best_lap.lap_time
                self.current_session.best_lap_number = self.best_lap.lap_number
            
            self.current_session.baseline_established = self.baseline_established
            self.current_session.driving_style = self.driving_style
            self.current_session.consistency_threshold = self.consistency_threshold
            
            # Save corner analysis
            corner_data = {}
            for corner, data in self.corner_analysis.items():
                corner_data[corner] = {
                    'brake_points': list(data['brake_points']),
                    'entry_speeds': list(data['entry_speeds']),
                    'exit_speeds': list(data['exit_speeds'])
                }
            self.current_session.corner_analysis = corner_data
            
            # Save to persistence
            self.persistence_manager.save_session(self.current_session)
            
        except Exception as e:
            logger.error(f"Failed to save session data: {e}")
    
    def _generate_baseline_countdown(self, telemetry: Dict[str, Any]) -> Optional[CoachingMessage]:
        """Generate countdown message showing laps remaining until baseline is established"""
        speed = telemetry.get('Speed', 0)  # Capital S for iRacing field
        if speed < 10:
            return None
        
        if self.baseline_just_established:
            self.baseline_just_established = False
            return CoachingMessage(
                message="🎉 AI Baseline established! Advanced coaching now active!",
                category="baseline",
                priority=8,
                confidence=100.0,
                data_source="baseline_completion"
            )
        
        if not self.baseline_established:
            completed_laps = len(self.laps)
            laps_remaining = max(0, 3 - completed_laps)
            
            if laps_remaining > 0:
                if completed_laps == 0:
                    message = f"🏁 Complete {laps_remaining} laps to establish AI baseline"
                else:
                    message = f"🏁 {laps_remaining} more laps for baseline ({completed_laps}/3)"
                
                return CoachingMessage(
                    message=message,
                    category="baseline",
                    priority=3,
                    confidence=100.0,
                    data_source="lap_tracking"
                )
        
        return None
    
    def _analyze_track_surface(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze track surface"""
        messages = []
        track_surface = telemetry.get('playerTrackSurface', 4)
        speed = telemetry.get('speed', 0)
        
        if track_surface == 1 and speed > 10:  # Off track
            messages.append(CoachingMessage(
                message="Off track - focus on consistency and racing line",
                category="racing_line",
                priority=7,
                confidence=80,
                data_source="track_surface"
            ))
        
        return messages
    
    def _analyze_brake_usage(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze braking patterns"""
        messages = []
        brake_pressure = telemetry.get('brake', 0)
        speed = telemetry.get('speed', 0)
        throttle = telemetry.get('throttle', 0)
        
        current_time = time.time()
        
        # Heavy braking detection (MUCH lower threshold for more frequent coaching)
        if brake_pressure > 25 and speed > 20:  # Lowered from 40% brake and 40mph
            if not hasattr(self, '_last_hard_brake') or current_time - self._last_hard_brake > 6:
                messages.append(CoachingMessage(
                    message="Heavy braking - try progressive braking for smoother cornering",
                    category="braking",
                    priority=5,
                    confidence=75,
                    data_source="brake_pressure"
                ))
                self._last_hard_brake = current_time
                logger.info(f"🔍 HEAVY BRAKING DETECTED: Brake={brake_pressure:.1f}%, Speed={speed:.1f}")
        
        # Trail braking detection (much lower threshold)
        if brake_pressure > 5 and throttle > 3:  # Both brake and throttle active
            if not hasattr(self, '_last_trail_brake') or current_time - self._last_trail_brake > 25:  # Longer cooldown
                if random.random() < 0.05:  # Only 5% chance for positive feedback
                    messages.append(CoachingMessage(
                        message="Trail braking detected - good technique for car rotation",
                        category="technique", 
                        priority=1,  # Lower priority
                        confidence=70,
                        data_source="trail_braking"
                    ))
                    self._last_trail_brake = current_time
        
        # Sudden brake release (lower threshold)
        if hasattr(self, '_last_brake_pressure'):
            brake_delta = self._last_brake_pressure - brake_pressure
            if brake_delta > 15 and speed > 20:  # Sudden brake release - lowered from 25/30
                if not hasattr(self, '_last_brake_release') or current_time - self._last_brake_release > 8:
                    messages.append(CoachingMessage(
                        message="Smooth brake release helps maintain car balance through corners",
                        category="braking",
                        priority=4,
                        confidence=65,
                        data_source="brake_release"
                    ))
                    self._last_brake_release = current_time
                    logger.info(f"🔍 SUDDEN BRAKE RELEASE: Delta={brake_delta:.1f}%, Speed={speed:.1f}")
        
        # Brake lockup prevention (lower threshold)
        if brake_pressure > 50 and speed > 50:  # Lowered from 70% brake and 80mph
            if not hasattr(self, '_last_lockup_warning') or current_time - self._last_lockup_warning > 10:
                messages.append(CoachingMessage(
                    message="High brake pressure at speed - watch for lockups and find the limit",
                    category="braking",
                    priority=6,
                    confidence=80,
                    data_source="lockup_prevention"
                ))
                self._last_lockup_warning = current_time
                logger.info(f"🔍 LOCKUP WARNING: Brake={brake_pressure:.1f}%, Speed={speed:.1f}")
        
        self._last_brake_pressure = brake_pressure
        return messages
    
    def _analyze_throttle_application(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze throttle usage patterns"""
        messages = []
        throttle = telemetry.get('throttle', 0)
        speed = telemetry.get('speed', 0)
        gear = telemetry.get('gear', 0)
        
        current_time = time.time()
        
        # Aggressive throttle application (MUCH lower threshold)
        if hasattr(self, '_last_throttle'):
            throttle_delta = throttle - self._last_throttle
            if throttle_delta > 15 and speed > 15:  # Sudden throttle increase - lowered from 20/20
                if not hasattr(self, '_last_aggressive_throttle') or current_time - self._last_aggressive_throttle > 6:
                    messages.append(CoachingMessage(
                        message="Sudden throttle input - smooth application maintains traction",
                        category="throttle",
                        priority=4,
                        confidence=70,
                        data_source="throttle_application"
                    ))
                    self._last_aggressive_throttle = current_time
                    logger.info(f"🔍 AGGRESSIVE THROTTLE: Delta={throttle_delta:.1f}%, Speed={speed:.1f}")
        
        # Full throttle at low speed (MUCH lower threshold for wheel spin)
        if throttle > 60 and speed < 35 and gear > 1:  # Lowered from 70% throttle and 40mph
            if not hasattr(self, '_last_wheel_spin') or current_time - self._last_wheel_spin > 6:
                messages.append(CoachingMessage(
                    message="High throttle at low speed - build up gradually to avoid wheelspin",
                    category="throttle",
                    priority=6,
                    confidence=80,
                    data_source="wheel_spin_risk"
                ))
                self._last_wheel_spin = current_time
                logger.info(f"🔍 WHEEL SPIN RISK: Throttle={throttle:.1f}%, Speed={speed:.1f}")
        
        # Good throttle modulation (much rarer positive feedback)
        if 30 < throttle < 70 and speed > 40:
            if not hasattr(self, '_last_good_throttle') or current_time - self._last_good_throttle > 45:  # Much longer cooldown
                if random.random() < 0.05:  # Only 5% chance
                    messages.append(CoachingMessage(
                        message="Good throttle modulation - smooth inputs give consistent performance",
                        category="technique",
                        priority=1,  # Lower priority
                        confidence=60,
                        data_source="throttle_control"
                    ))
                    self._last_good_throttle = current_time
        
        # Throttle control in corners (new detection)
        if throttle > 80 and speed < 80:  # High throttle at medium-low speeds
            if not hasattr(self, '_last_corner_throttle') or current_time - self._last_corner_throttle > 8:
                messages.append(CoachingMessage(
                    message="Corner exit detected - progressive throttle helps maintain grip",
                    category="racing_line",
                    priority=4,
                    confidence=65,
                    data_source="corner_throttle"
                ))
                self._last_corner_throttle = current_time
        
        # Original wheel spin detection (much lower threshold)
        if throttle > 85 and speed < 50:
            if not hasattr(self, '_last_throttle_warning') or current_time - self._last_throttle_warning > 5:
                messages.append(CoachingMessage(
                    message="Maximum throttle at low speed - risk of wheelspin and time loss",
                    category="throttle",
                    priority=5,
                    confidence=75,
                    data_source="throttle_speed"
                ))
                self._last_throttle_warning = current_time
        
        self._last_throttle = throttle
        return messages
    
    def _analyze_speed_management(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze speed management and racing line"""
        messages = []
        speed = telemetry.get('speed', 0)
        gear = telemetry.get('gear', 0)
        throttle = telemetry.get('throttle', 0)
        brake = telemetry.get('brake', 0)
        
        current_time = time.time()
        
        # Coasting detection (much lower threshold)
        if speed > 50 and throttle < 15 and brake < 10:  # Lowered from 80mph
            if not hasattr(self, '_last_coasting') or current_time - self._last_coasting > 8:
                messages.append(CoachingMessage(
                    message="Coasting detected - maintain momentum or prepare for next input",
                    category="racing_line",
                    priority=3,
                    confidence=65,
                    data_source="speed_management"
                ))
                self._last_coasting = current_time
        
        # Gear and speed mismatch (lower threshold)
        if speed > 70 and gear > 0 and gear < 4:  # Lowered from 100mph
            if not hasattr(self, '_last_gear_speed') or current_time - self._last_gear_speed > 6:
                messages.append(CoachingMessage(
                    message="Low gear at high speed - consider upshifting for better efficiency",
                    category="technique",
                    priority=4,
                    confidence=70,
                    data_source="gear_speed_ratio"
                ))
                self._last_gear_speed = current_time
        
        # Corner entry speed detection (new lower threshold)
        if speed > 90 and brake > 30:
            if not hasattr(self, '_last_corner_entry') or current_time - self._last_corner_entry > 10:
                messages.append(CoachingMessage(
                    message="High speed braking - ensure you can make the corner at this pace",
                    category="racing_line",
                    priority=5,
                    confidence=75,
                    data_source="corner_entry"
                ))
                self._last_corner_entry = current_time
        
        # Speed transitions (much lower threshold for better detection)
        if hasattr(self, '_last_speed'):
            speed_delta = speed - self._last_speed
            if speed_delta > 5 and throttle > 40:  # Good acceleration (lowered threshold)
                if not hasattr(self, '_last_good_accel') or current_time - self._last_good_accel > 30:  # Longer cooldown
                    if random.random() < 0.05:  # Only 5% chance for positive feedback
                        messages.append(CoachingMessage(
                            message="Good acceleration phase - exit speed is building lap time",
                            category="racing_line",
                            priority=1,  # Lower priority
                            confidence=60,
                            data_source="acceleration"
                        ))
                        self._last_good_accel = current_time
            
            # Rapid deceleration (corner approach)
            elif speed_delta < -8 and brake > 20:
                if not hasattr(self, '_last_decel') or current_time - self._last_decel > 12:
                    messages.append(CoachingMessage(
                        message="Braking zone approach - consistent braking points build confidence",
                        category="braking",
                        priority=3,
                        confidence=65,
                        data_source="deceleration"
                    ))
                    self._last_good_accel = current_time
        
        self._last_speed = speed
        return messages
    
    def _analyze_driving_rhythm(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze overall driving rhythm and flow"""
        messages = []
        throttle = telemetry.get('throttle', 0)
        brake = telemetry.get('brake', 0)
        speed = telemetry.get('speed', 0)
        # Fix steering field name and add fallback
        steering_angle = abs(telemetry.get('steering', telemetry.get('steerAngle', 0)))  
        
        current_time = time.time()
        
        # Debug log to see actual steering values
        if steering_angle > 0.1:  # Only log when there's actual steering input
            logger.debug(f"🎮 Steering input detected: {steering_angle:.2f}°, Speed: {speed:.1f}, Throttle: {throttle:.1f}%, Brake: {brake:.1f}%")
        
        # Frequent input changes (potential overdriving) - much lower threshold
        if hasattr(self, '_last_inputs'):
            throttle_change = abs(throttle - self._last_inputs.get('throttle', 0))
            brake_change = abs(brake - self._last_inputs.get('brake', 0))
            steering_change = abs(steering_angle - self._last_inputs.get('steering', 0))
            
            if throttle_change > 10 or brake_change > 10 or steering_change > 3:  # Much more sensitive
                self._input_changes = getattr(self, '_input_changes', 0) + 1
            else:
                self._input_changes = max(0, getattr(self, '_input_changes', 0) - 1)
            
            # Too many input changes suggests overdriving - lower threshold
            if self._input_changes > 6:  # Much lower threshold
                if not hasattr(self, '_last_overdriving') or current_time - self._last_overdriving > 8:
                    messages.append(CoachingMessage(
                        message="Many corrections detected - try smoother, more deliberate inputs",
                        category="technique",
                        priority=5,
                        confidence=75,
                        data_source="input_analysis"
                    ))
                    self._last_overdriving = current_time
                    self._input_changes = 0
        
        # Oversteer detection (MUCH lower threshold)
        if steering_angle > 5 and throttle > 30 and speed > 15:  # Much more sensitive
            if not hasattr(self, '_last_oversteer') or current_time - self._last_oversteer > 8:
                messages.append(CoachingMessage(
                    message="High steering angle under throttle - possible oversteer, ease off throttle",
                    category="technique",
                    priority=6,
                    confidence=80,
                    data_source="oversteer_detection"
                ))
                self._last_oversteer = current_time
                logger.info(f"🔍 OVERSTEER DETECTED: Steering={steering_angle:.2f}°, Throttle={throttle:.1f}%, Speed={speed:.1f}")
        
        # Understeer detection (MUCH lower threshold)
        if steering_angle > 8 and speed > 25:  # Much more sensitive
            if not hasattr(self, '_last_understeer') or current_time - self._last_understeer > 10:
                messages.append(CoachingMessage(
                    message="High steering angle - if car isn't turning, reduce speed into corner",
                    category="technique",
                    priority=5,
                    confidence=70,
                    data_source="understeer_detection"
                ))
                self._last_understeer = current_time
                logger.info(f"🔍 UNDERSTEER DETECTED: Steering={steering_angle:.2f}°, Speed={speed:.1f}")
        
        # Both throttle and brake pressed (lower threshold)
        if throttle > 15 and brake > 15:
            if not hasattr(self, '_last_mixed_inputs') or current_time - self._last_mixed_inputs > 8:
                messages.append(CoachingMessage(
                    message="Overlapping brake and throttle - separate inputs for better control",
                    category="technique",
                    priority=6,
                    confidence=80,
                    data_source="mixed_inputs"
                ))
                self._last_mixed_inputs = current_time
        
        # Good smooth driving detected (very rare positive feedback)
        if hasattr(self, '_last_inputs'):
            throttle_smooth = abs(throttle - self._last_inputs.get('throttle', 0)) < 8
            brake_smooth = abs(brake - self._last_inputs.get('brake', 0)) < 8
            steering_smooth = abs(steering_angle - self._last_inputs.get('steering', 0)) < 4
            
            if throttle_smooth and brake_smooth and steering_smooth and speed > 30:
                self._smooth_count = getattr(self, '_smooth_count', 0) + 1
                if self._smooth_count > 50:  # About 5 seconds of smooth driving
                    if not hasattr(self, '_last_smooth_driving') or current_time - self._last_smooth_driving > 60:  # 1 minute cooldown
                        if random.random() < 0.05:  # Only 5% chance
                            messages.append(CoachingMessage(
                                message="Great driving rhythm - smooth inputs build consistency and speed",
                                category="technique",
                                priority=1,
                                confidence=65,
                                data_source="smooth_driving"
                            ))
                            self._last_smooth_driving = current_time
                        self._smooth_count = 0
            else:
                self._smooth_count = 0
        
        self._last_inputs = {'throttle': throttle, 'brake': brake, 'steering': steering_angle}
        return messages
    
    def _analyze_sector_performance(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze performance in different track sections"""
        messages = []
        speed = telemetry.get('speed', 0)
        
        current_time = time.time()
        
        # Track different speed zones to give sector-specific advice
        if not hasattr(self, '_speed_zones'):
            self._speed_zones = {'high': [], 'medium': [], 'low': []}
        
        # Categorize current speed zone
        if speed > 120:
            zone = 'high'
            zone_message = "High speed section - focus on smooth inputs and racing line"
        elif speed > 60:
            zone = 'medium'
            zone_message = "Medium speed section - balance between speed and control"
        elif speed > 20:
            zone = 'low'
            zone_message = "Slow section - prioritize exit speed for the next straight"
        else:
            return messages
        
        # Add to zone history
        self._speed_zones[zone].append(current_time)
        
        # Clean old entries (keep last 30 seconds)
        for z in self._speed_zones:
            self._speed_zones[z] = [t for t in self._speed_zones[z] if current_time - t < 30]
        
        # Give zone-specific advice periodically
        if len(self._speed_zones[zone]) == 1:  # First time in this zone in a while
            zone_advice_key = f'_last_{zone}_zone_advice'
            if not hasattr(self, zone_advice_key) or current_time - getattr(self, zone_advice_key) > 20:
                messages.append(CoachingMessage(
                    message=zone_message,
                    category="racing_line",
                    priority=2,
                    confidence=60,
                    data_source=f"{zone}_speed_zone"
                ))
                setattr(self, zone_advice_key, current_time)
        
        return messages
    
    def _analyze_consistency(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze lap-to-lap consistency"""
        messages = []
        
        if len(self.laps) < 3:
            return messages
        
        recent_laps = self.laps[-5:]
        lap_times = [lap.lap_time for lap in recent_laps if lap.lap_time > 0]
        
        if len(lap_times) >= 3:
            std_time = np.std(lap_times)
            
            if std_time > 2.0:  # More than 2 second variation
                messages.append(CoachingMessage(
                    message=f"Focus on consistency - lap times varying by {std_time:.3f}s",
                    category="general",
                    priority=7,
                    confidence=80,
                    data_source="lap_times"
                ))
        
        return messages
    
    def _analyze_situational_awareness(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze situational awareness and driving context"""
        messages = []
        current_time = time.time()
        
        speed = telemetry.get('speed', 0)
        gear = telemetry.get('gear', 1)
        rpm = telemetry.get('engineRpm', 0)
        fuel = telemetry.get('fuel', 100)
        brake_temp = telemetry.get('brakeTempAvgLF', 0)
        
        # Low fuel awareness
        if fuel < 20 and random.random() < 0.1:
            if "Low fuel - consider fuel saving techniques" not in self.recent_messages or \
               current_time - self.recent_messages["Low fuel - consider fuel saving techniques"] > self.message_cooldown * 4:
                messages.append(CoachingMessage(
                    message="Low fuel - consider fuel saving techniques",
                    category="tip",
                    priority=4,
                    confidence=95,
                    data_source="situational_awareness"
                ))
        
        # High brake temperatures
        if brake_temp > 600 and random.random() < 0.15:
            if "Brake temps are high - give them some cooling time" not in self.recent_messages or \
               current_time - self.recent_messages["Brake temps are high - give them some cooling time"] > self.message_cooldown * 3:
                messages.append(CoachingMessage(
                    message="Brake temps are high - give them some cooling time",
                    category="braking",
                    priority=4,
                    confidence=90,
                    data_source="situational_awareness"
                ))
        
        # Gear and speed relationship awareness
        if gear > 3 and speed < 100 and random.random() < 0.08:
            if "Check your gear selection - you might be lugging the engine" not in self.recent_messages or \
               current_time - self.recent_messages["Check your gear selection - you might be lugging the engine"] > self.message_cooldown * 4:
                messages.append(CoachingMessage(
                    message="Check your gear selection - you might be lugging the engine",
                    category="technique",
                    priority=3,
                    confidence=75,
                    data_source="situational_awareness"
                ))
        
        # High RPM awareness
        if rpm > 7500 and random.random() < 0.12:
            if "High RPMs - consider upshifting to preserve the engine" not in self.recent_messages or \
               current_time - self.recent_messages["High RPMs - consider upshifting to preserve the engine"] > self.message_cooldown * 3:
                messages.append(CoachingMessage(
                    message="High RPMs - consider upshifting to preserve the engine",
                    category="technique",
                    priority=3,
                    confidence=85,
                    data_source="situational_awareness"
                ))
        
        # Session duration awareness
        session_duration = current_time - self.session_start_time
        if session_duration > 600 and len(self.laps) < 5:  # Long session, few laps
            if random.random() < 0.05:
                if "Taking your time is good - quality over quantity" not in self.recent_messages or \
                   current_time - self.recent_messages["Taking your time is good - quality over quantity"] > self.message_cooldown * 5:
                    messages.append(CoachingMessage(
                        message="Taking your time is good - quality over quantity",
                        category="tip",
                        priority=2,
                        confidence=80,
                        data_source="situational_awareness"
                    ))
        
        return messages

    def _generate_progressive_coaching(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Generate coaching messages that adapt to session progression"""
        messages = []
        current_time = time.time()
        lap_count = len(self.laps)
        session_duration = current_time - self.session_start_time
        
        # Early session (first 3 laps) - focus on basics and track learning
        if lap_count <= 3:
            early_coaching = [
                "Take time to learn the track - speed comes with familiarity",
                "Focus on hitting your marks consistently",
                "Feel the car's balance through each corner",
                "Don't worry about lap times yet - learn the racing line",
                "Each lap is data - observe how the car responds"
            ]
            
            if random.random() < 0.03:  # Much lower: 3% chance per analysis
                message = random.choice(early_coaching)
                if message not in self.recent_messages or \
                   current_time - self.recent_messages[message] > self.message_cooldown * 5:
                    messages.append(CoachingMessage(
                        message=message,
                        category="baseline",
                        priority=3,
                        confidence=85,
                        data_source="progressive_coaching"
                    ))
        
        # Mid session (4-8 laps) - focus on consistency and refinement
        elif 4 <= lap_count <= 8:
            mid_coaching = [
                "Now focus on consistency - nail the same line every lap",
                "Small improvements each lap add up to big gains",
                "Are you hitting your braking points consistently?",
                "Smooth driving is fast driving - eliminate jerky inputs",
                "Notice which corners cost you the most time"
            ]
            
            if random.random() < 0.02:  # Much lower: 2% chance per analysis
                message = random.choice(mid_coaching)
                if message not in self.recent_messages or \
                   current_time - self.recent_messages[message] > self.message_cooldown * 5:
                    messages.append(CoachingMessage(
                        message=message,
                        category="technique",
                        priority=3,
                        confidence=88,
                        data_source="progressive_coaching"
                    ))
        
        # Late session (9+ laps) - focus on optimization and race craft
        elif lap_count >= 9:
            late_coaching = [
                "Time to push - you know the track, trust your instincts",
                "Look for those final tenths - optimize your line",
                "Consistency is your foundation - now add speed",
                "Focus on your weakest sectors - that's where time hides",
                "Race pace isn't just speed - it's sustainable speed"
            ]
            
            if random.random() < 0.01:  # Much lower: 1% chance per analysis
                message = random.choice(late_coaching)
                if message not in self.recent_messages or \
                   current_time - self.recent_messages[message] > self.message_cooldown * 5:
                    messages.append(CoachingMessage(
                        message=message,
                        category="racing_line",
                        priority=3,
                        confidence=90,
                        data_source="progressive_coaching"
                    ))
        
        # Special motivational messages for longer sessions
        if session_duration > 1200:  # 20+ minutes
            if random.random() < 0.05:  # 5% chance
                messages.append(CoachingMessage(
                    message="Great session length! Consistency over many laps builds real speed",
                    category="tip",
                    priority=2,
                    confidence=95,
                    data_source="progressive_coaching"
                ))
        
        return messages

    def _generate_general_tips(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Generate general coaching tips"""
        messages = []
        current_time = time.time()
        
        # Varied coaching tips by category
        driving_technique_tips = [
            "Focus on smooth inputs - consistency beats speed",
            "Look ahead - where you look is where you'll go",
            "Exit speed matters more than entry speed",
            "Weight transfer is everything - smooth transitions",
            "The fastest line isn't always the racing line",
            "Patience in corners leads to speed on straights"
        ]
        
        track_craft_tips = [
            "Use reference points for consistent braking",
            "Find your markers - apex, turn-in, track-out",
            "Late apex corners reward patient drivers",
            "Trail braking helps rotate the car naturally",
            "Maximize track width - use every inch available",
            "Learn the track's rhythm - fast flows faster"
        ]
        
        car_control_tips = [
            "Feel the car through your hands and seat",
            "Oversteer? Reduce throttle before steering",
            "Understeer? Reduce speed, not steering angle",
            "The car will tell you its limits - listen",
            "Smooth wheel movements preserve tire grip",
            "Progressive inputs give progressive responses"
        ]
        
        mental_game_tips = [
            "Stay relaxed - tension kills smoothness",
            "Drive your own race, not someone else's",
            "Focus on process, not lap times",
            "Mistakes are learning opportunities",
            "Consistency builds confidence and speed",
            "Trust your instincts and the car"
        ]
        
        # Combine all tips
        all_tips = driving_technique_tips + track_craft_tips + car_control_tips + mental_game_tips
        
        # Generate tip extremely rarely - every 180-300 seconds (3-5 minutes)
        tip_interval = random.uniform(180, 300)
        if len(messages) == 0 and current_time % tip_interval < 1:
            # Only 1% chance even when interval is hit
            if random.random() < 0.01:
                selected_tip = random.choice(all_tips)
                if selected_tip not in self.recent_messages or \
                   current_time - self.recent_messages[selected_tip] > self.message_cooldown * 10:  # Much longer cooldown for tips
                    messages.append(CoachingMessage(
                        message=selected_tip,
                        category="tip",
                        priority=1,  # Lower priority than specific coaching
                        confidence=90,
                        data_source="general_tips"
                    ))
        
        return messages
    
    def _prioritize_messages(self, messages: List[CoachingMessage]) -> List[CoachingMessage]:
        """Filter and prioritize coaching messages"""
        current_time = time.time()
        
        # Filter out duplicate messages
        filtered_messages = []
        for message in messages:
            if message.message not in self.recent_messages:
                filtered_messages.append(message)
                self.recent_messages[message.message] = current_time
        
        # Clean up old messages
        expired_messages = [msg for msg, timestamp in self.recent_messages.items() 
                          if current_time - timestamp > self.message_cooldown]
        for msg in expired_messages:
            del self.recent_messages[msg]
        
        # Sort by priority and return top 3
        filtered_messages.sort(key=lambda x: x.priority, reverse=True)
        return filtered_messages[:3]
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get current session summary"""
        return {
            "laps_completed": len(self.laps),
            "best_lap_time": self.best_lap.lap_time if self.best_lap else None,
            "baseline_established": self.baseline_established,
            "driving_style": self.driving_style,
            "track_name": self.track_name,
            "car_name": self.car_name,
            "session_duration": time.time() - self.session_start_time
        }
    
    def finish_session(self):
        """Finish current session and save final data"""
        if self.current_session:
            self.current_session.end_time = time.time()
            self._save_session_data()
            logger.info(f"📝 Session finished: {self.current_session.session_id}")
    
    def get_previous_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get previous sessions for current track/car"""
        if not self.track_name or not self.car_name:
            return []
        
        sessions = self.persistence_manager.find_previous_sessions(
            self.track_name, self.car_name, limit
        )
        
        return [
            {
                'session_id': s.session_id,
                'start_time': s.start_time,
                'best_lap_time': s.best_lap_time,
                'laps_count': len(s.laps),
                'baseline_established': s.baseline_established
            } for s in sessions
        ]
    
    # LLM Coaching Methods
    def _generate_llm_coaching(self, telemetry: Dict[str, float]) -> List[CoachingMessage]:
        """Generate natural language coaching using LLM with track-specific context"""
        if not self.llm_enabled or not self.llm_api_key or self.llm_api_key == "your-openai-api-key-here":
            return []
        
        current_time = time.time()
        if current_time - self.last_llm_message < self.llm_cooldown:
            return []
        
        # Log telemetry for debugging (every 30 frames to avoid spam)
        if hasattr(self, '_debug_counter'):
            self._debug_counter += 1
        else:
            self._debug_counter = 0
            
        if self._debug_counter % 30 == 0:  # Log every 30 telemetry updates
            speed = telemetry.get('Speed', 0)
            logger.info(f"🔍 Telemetry check: Speed={speed:.1f}, Brake={telemetry.get('Brake', 0):.2f}, Throttle={telemetry.get('Throttle', 0):.2f}, Steering={telemetry.get('SteeringWheelAngle', 0):.2f}")
        
        # Detect coaching situation with generic sections
        coaching_moment = self._detect_coaching_moments(telemetry)
        if not coaching_moment:
            return []
        
        # Get enhanced track-specific context combining track name + sections
        enhanced_context = self._get_track_specific_context(telemetry, coaching_moment)
        
        # Log current context for debugging
        speed = telemetry.get('Speed', 0)
        logger.info(f"🎯 LLM coaching triggered for: {enhanced_context}")
        logger.info(f"   📊 Telemetry: Speed={speed:.1f}, Brake={telemetry.get('Brake', 0):.2f}, Throttle={telemetry.get('Throttle', 0):.2f}, Steering={telemetry.get('SteeringWheelAngle', 0):.2f}")
        
        # Generate LLM message with enhanced track-specific context
        llm_message = self._call_openai_llm(enhanced_context, telemetry)
        if llm_message:
            self.last_llm_message = current_time
            logger.info(f"🤖 Generated track-specific LLM message: '{llm_message}'")
            return [CoachingMessage(
                message=llm_message,
                category="llm",
                priority=5,
                confidence=80.0,
                data_source="LLM_track_specific_analysis",
                improvement_potential=0.1
            )]
        
        return []
    
    def _detect_coaching_moments(self, telemetry: Dict[str, float]) -> str:
        """Detect specific coaching moments for LLM context"""
        if len(self.telemetry_buffer) < 10:  # Reduced requirement
            return None
        
        recent_data = list(self.telemetry_buffer)[-30:] if len(self.telemetry_buffer) >= 30 else list(self.telemetry_buffer)
        current_section = self._get_track_section(telemetry.get('LapDistPct', 0))
        
        # Heavy braking - much more sensitive for hobbyist drivers
        current_brake = telemetry.get('Brake', 0)
        current_speed = telemetry.get('Speed', 0)
        
        # Convert speed if it's in m/s (iRacing SDK default)
        if current_speed < 10:  # Assume m/s if speed is very low
            current_speed_mph = current_speed * 2.237  # m/s to mph
        else:
            current_speed_mph = current_speed  # Already in mph
        
        if current_brake >= 0.5 and current_speed_mph > 40:  # Hobbyist: 50%+ brake at 40mph
            return f"heavy_braking_into_{current_section.lower().replace(' ', '_')}"
        
        # Throttle control issues - much more sensitive
        current_throttle = telemetry.get('Throttle', 0)
        if len(recent_data) >= 5:
            throttle_changes = []
            for i in range(max(0, len(recent_data)-5), len(recent_data)):
                if i > 0:
                    throttle_changes.append(abs(recent_data[i].get('Throttle', 0) - recent_data[i-1].get('Throttle', 0)))
            
            if throttle_changes and max(throttle_changes) >= 0.15:  # Hobbyist: 15%+ throttle changes
                return f"throttle_control_issue_at_{current_section.lower().replace(' ', '_')}"
        
        # Simple steering detection for hobbyist learning
        steering_angle = telemetry.get('SteeringWheelAngle', 0)
        if abs(steering_angle) >= 0.25:  # Hobbyist: Any 25°+ steering gives tips
            return f"handling_tip_at_{current_section.lower().replace(' ', '_')}"
        
        # Corner exit issues - much more sensitive for learning
        if current_throttle >= 0.4 and abs(steering_angle) >= 0.2:  # Hobbyist: 40%+ throttle + 20°+ steering
            return f"corner_exit_at_{current_section.lower().replace(' ', '_')}"
        
        # Medium-high speed coaching (helpful for hobbyists)
        if current_speed_mph >= 90:  # Hobbyist: 90mph+ for speed tips
            return f"high_speed_section_{current_section.lower().replace(' ', '_')}"
        
        # Late braking detection (common hobbyist issue)
        if current_brake >= 0.3 and current_speed_mph > 60:  # Hobbyist: 30%+ brake at speed
            return f"late_braking_at_{current_section.lower().replace(' ', '_')}"
        
        return None
    
    def _get_track_section(self, lap_pct: float) -> str:
        """Get current track section name for context"""
        section_key = round(lap_pct, 1)
        return self.track_sections.get(section_key, "Unknown Section")
    
    def _call_openai_llm(self, coaching_context: str, telemetry: Dict[str, float]) -> str:
        """Call OpenAI LLM to generate coaching message with track-specific context"""
        try:
            current_section = self._get_track_section(telemetry.get('LapDistPct', 0))
            speed = telemetry.get('Speed', 0) * 2.237  # Convert to MPH
            throttle = telemetry.get('Throttle', 0) * 100
            brake = telemetry.get('Brake', 0) * 100
            
            # Get dynamic track information from telemetry
            track_name = telemetry.get('trackDisplayName', self.track_name or 'Unknown Track')
            track_config = telemetry.get('trackConfigName', '')
            car_name = telemetry.get('driverCarName', self.car_name or 'GT3 Car')
            
            # Build full track context
            full_track_name = track_name
            if track_config and track_config.strip():
                full_track_name += f" - {track_config}"
            
            # Create track-specific coaching prompt
            prompt = f"""You are an expert racing coach for GT3 cars. Based on the telemetry data, give ONE brief, specific coaching tip for {full_track_name}.

Car: {car_name}
Track: {full_track_name}
Current situation: {coaching_context}
Track section: {current_section}
Speed: {speed:.0f} mph
Throttle: {throttle:.0f}%
Brake: {brake:.0f}%

Use your knowledge of {track_name} to give track-specific advice. Consider the unique characteristics of this track layout, elevation changes, corner sequences, and optimal racing lines.

Respond with just the coaching message, like:
- "Brake earlier for Fuji's T1 hairpin"
- "Carry more speed through Silverstone's Maggotts"
- "Use all the kerb at Spa's Eau Rouge"
- "Watch the elevation change at COTA T1"

Keep it under 60 characters and speak directly to the driver."""

            headers = {
                'Authorization': f'Bearer {self.llm_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.llm_model,
                'messages': [
                    {'role': 'system', 'content': 'You are a concise racing coach. Respond with only the coaching message, no explanations.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 50,
                'temperature': 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result['choices'][0]['message']['content'].strip()
                # Clean up the message
                message = message.replace('"', '').replace("'", '')
                logger.info(f"🤖 LLM generated message: {message}")
                return message[:60]  # Ensure it's under 60 chars
            elif response.status_code == 429:
                logger.warning("🤖 LLM API rate limited - using fallback message")
                # Fallback messages based on context
                fallbacks = {
                    'heavy_braking': "Try braking earlier there",
                    'throttle_control': "Smooth out your throttle",
                    'steering_correction': "Less aggressive steering",
                    'corner_exit': "Ease off the throttle on exit",
                    'high_speed': "Careful with your speed"
                }
                for key, fallback in fallbacks.items():
                    if key in coaching_context:
                        return fallback
                return "Smooth and consistent"
            else:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"LLM coaching error: {e}")
            return None
    
    def _get_track_specific_context(self, telemetry: Dict[str, float], coaching_moment: str) -> str:
        """Enhanced coaching context that combines track name with section analysis"""
        # Get dynamic track information
        track_name = telemetry.get('trackDisplayName', self.track_name or 'Unknown Track')
        track_config = telemetry.get('trackConfigName', '')
        car_name = telemetry.get('driverCarName', self.car_name or 'GT3 Car')
        
        # Get generic section from lap position
        current_section = self._get_track_section(telemetry.get('LapDistPct', 0))
        lap_pct = telemetry.get('LapDistPct', 0)
        
        # Build full track context
        full_track_name = track_name
        if track_config and track_config.strip():
            full_track_name += f" - {track_config}"
        
        # Create enhanced context combining specific track + generic section + coaching moment
        context_parts = []
        
        # Add track-specific context
        if track_name and track_name not in ['Unknown Track', 'iRacing Track']:
            context_parts.append(f"at {full_track_name}")
        
        # Add section context with lap position
        if current_section and current_section != 'Unknown Section':
            section_pct = f"({lap_pct:.1%} through lap)"
            context_parts.append(f"in {current_section} {section_pct}")
        
        # Add coaching moment context
        if coaching_moment:
            # Clean up the coaching moment for better readability
            moment_clean = coaching_moment.replace('_', ' ').replace('at ', '').replace('into ', '')
            context_parts.append(f"experiencing {moment_clean}")
        
        # Combine all context parts
        if context_parts:
            return " - ".join(context_parts)
        else:
            return f"driving {car_name} around the track"
    
    def _detect_all_coaching_situations(self, telemetry: Dict[str, Any]) -> List[str]:
        """Comprehensive driving analysis - detect ALL problem areas and coaching opportunities"""
        situations = []
        current_time = time.time()
        
        # Get telemetry values
        speed = telemetry.get('speed', 0)
        throttle = telemetry.get('throttle', 0)
        brake = telemetry.get('brake', 0)
        steering = telemetry.get('steering', 0)
        track_surface = telemetry.get('playerTrackSurface', 4)
        gear = telemetry.get('gear', 1)
        rpm = telemetry.get('rpm', 0)
        fuel = telemetry.get('fuelLevel', 100)
        delta_time = telemetry.get('deltaTime', 0)
        lap_pct = telemetry.get('lapDistPct', 0)
        yaw_rate = telemetry.get('yawRate', 0)
        lat_accel = telemetry.get('latAccel', 0)
        long_accel = telemetry.get('longAccel', 0)
        
        # Only coach if moving meaningfully
        if speed < 5:
            return situations
        
        # Track the last time each situation was detected to avoid spam
        if not hasattr(self, '_situation_cooldowns'):
            self._situation_cooldowns = {}
        if not hasattr(self, '_telemetry_history'):
            self._telemetry_history = []
        
        # Store telemetry history for analysis (last 5 seconds at 60Hz = 300 samples)
        self._telemetry_history.append({
            'time': current_time,
            'speed': speed,
            'throttle': throttle,
            'brake': brake,
            'steering': steering,
            'delta_time': delta_time,
            'lap_pct': lap_pct,
            'gear': gear,
            'rpm': rpm
        })
        
        # Keep only last 300 samples (5 seconds)
        if len(self._telemetry_history) > 300:
            self._telemetry_history.pop(0)
        
        def can_trigger_situation(situation_name: str, cooldown: float = 5.0) -> bool:
            last_time = self._situation_cooldowns.get(situation_name, 0)
            return current_time - last_time > cooldown
        
        # ===== COMPREHENSIVE DRIVING ANALYSIS =====
        
        # 1. BRAKING ANALYSIS - All types of braking issues
        if brake > 1 and speed > 10:  # Any braking detected
            if brake > 80 and can_trigger_situation('panic_braking', 8.0):
                situations.append('panic_braking')
                self._situation_cooldowns['panic_braking'] = current_time
                logger.info(f"🚨 ANALYSIS: panic_braking (brake={brake:.1f}%, speed={speed:.1f})")
            
            elif brake > 50 and can_trigger_situation('heavy_braking', 6.0):
                situations.append('heavy_braking')
                self._situation_cooldowns['heavy_braking'] = current_time
                logger.info(f"🚨 ANALYSIS: heavy_braking (brake={brake:.1f}%, speed={speed:.1f})")
            
            elif brake > 15 and can_trigger_situation('moderate_braking', 5.0):
                situations.append('moderate_braking')
                self._situation_cooldowns['moderate_braking'] = current_time
                logger.info(f"🚨 ANALYSIS: moderate_braking (brake={brake:.1f}%, speed={speed:.1f})")
        
        # Analyze braking consistency
        if len(self._telemetry_history) >= 30:  # 0.5 seconds of data
            recent_brake = [h['brake'] for h in self._telemetry_history[-30:]]
            brake_variance = np.var(recent_brake) if len(recent_brake) > 1 else 0
            if brake_variance > 100 and max(recent_brake) > 10 and can_trigger_situation('inconsistent_braking', 8.0):
                situations.append('inconsistent_braking')
                self._situation_cooldowns['inconsistent_braking'] = current_time
                logger.info(f"🚨 ANALYSIS: inconsistent_braking (variance={brake_variance:.1f})")
        
        # 2. THROTTLE ANALYSIS - All throttle control issues
        if hasattr(self, '_last_throttle'):
            throttle_delta = abs(throttle - self._last_throttle)
            
            # Sudden throttle changes
            if throttle_delta > 15 and can_trigger_situation('abrupt_throttle', 4.0):
                situations.append('abrupt_throttle')
                self._situation_cooldowns['abrupt_throttle'] = current_time
                logger.info(f"🚨 ANALYSIS: abrupt_throttle (delta={throttle_delta:.1f}%)")
            
            # Wheel spin risk
            if throttle > 30 and speed < 40 and gear > 1 and can_trigger_situation('traction_risk', 5.0):
                situations.append('traction_risk')
                self._situation_cooldowns['traction_risk'] = current_time
                logger.info(f"🚨 ANALYSIS: traction_risk (throttle={throttle:.1f}%, speed={speed:.1f})")
        
        # Throttle smoothness analysis
        if len(self._telemetry_history) >= 60:  # 1 second of data
            recent_throttle = [h['throttle'] for h in self._telemetry_history[-60:]]
            throttle_variance = np.var(recent_throttle) if len(recent_throttle) > 1 else 0
            if throttle_variance > 50 and max(recent_throttle) > 20 and can_trigger_situation('jerky_throttle', 10.0):
                situations.append('jerky_throttle')
                self._situation_cooldowns['jerky_throttle'] = current_time
                logger.info(f"🚨 ANALYSIS: jerky_throttle (variance={throttle_variance:.1f})")
        
        # 3. STEERING & HANDLING ANALYSIS - All handling issues
        steering_magnitude = abs(steering)
        
        if steering_magnitude > 1 and speed > 10:  # Any steering input
            if steering_magnitude > 20 and speed > 30 and can_trigger_situation('excessive_steering', 6.0):
                situations.append('excessive_steering')
                self._situation_cooldowns['excessive_steering'] = current_time
                logger.info(f"🚨 ANALYSIS: excessive_steering (steering={steering:.1f}°, speed={speed:.1f})")
            
            elif steering_magnitude > 10 and speed > 50 and can_trigger_situation('high_speed_steering', 8.0):
                situations.append('high_speed_steering')
                self._situation_cooldowns['high_speed_steering'] = current_time
                logger.info(f"🚨 ANALYSIS: high_speed_steering (steering={steering:.1f}°, speed={speed:.1f})")
        
        # Steering smoothness analysis
        if len(self._telemetry_history) >= 30:
            recent_steering = [h['steering'] for h in self._telemetry_history[-30:]]
            steering_variance = np.var(recent_steering) if len(recent_steering) > 1 else 0
            if steering_variance > 25 and max([abs(s) for s in recent_steering]) > 5 and can_trigger_situation('unstable_steering', 8.0):
                situations.append('unstable_steering')
                self._situation_cooldowns['unstable_steering'] = current_time
                logger.info(f"🚨 ANALYSIS: unstable_steering (variance={steering_variance:.1f})")
        
        # 4. RACING LINE & TRACK POSITION ANALYSIS
        if track_surface == 1 and speed > 10 and can_trigger_situation('off_track_excursion', 10.0):
            situations.append('off_track_excursion')
            self._situation_cooldowns['off_track_excursion'] = current_time
            logger.info(f"🚨 ANALYSIS: off_track_excursion (speed={speed:.1f})")
        
        # 5. SPEED MANAGEMENT ANALYSIS
        if len(self._telemetry_history) >= 120:  # 2 seconds of data
            recent_speeds = [h['speed'] for h in self._telemetry_history[-120:]]
            speed_variance = np.var(recent_speeds) if len(recent_speeds) > 1 else 0
            
            if speed_variance > 100 and max(recent_speeds) > 20 and can_trigger_situation('inconsistent_speed', 12.0):
                situations.append('inconsistent_speed')
                self._situation_cooldowns['inconsistent_speed'] = current_time
                logger.info(f"🚨 ANALYSIS: inconsistent_speed (variance={speed_variance:.1f})")
        
        # Corner speed analysis
        if steering_magnitude > 5:  # In a corner
            if speed > 80 and can_trigger_situation('corner_too_fast', 10.0):
                situations.append('corner_too_fast')
                self._situation_cooldowns['corner_too_fast'] = current_time
                logger.info(f"🚨 ANALYSIS: corner_too_fast (speed={speed:.1f}, steering={steering:.1f}°)")
            
            elif speed < 25 and speed > 10 and can_trigger_situation('corner_too_slow', 15.0):
                situations.append('corner_too_slow')
                self._situation_cooldowns['corner_too_slow'] = current_time
                logger.info(f"🚨 ANALYSIS: corner_too_slow (speed={speed:.1f}, steering={steering:.1f}°)")
        
        # 6. GEAR & RPM ANALYSIS
        if rpm > 0:
            # High RPM analysis
            if rpm > 7500 and can_trigger_situation('high_rpm', 8.0):
                situations.append('high_rpm')
                self._situation_cooldowns['high_rpm'] = current_time
                logger.info(f"🚨 ANALYSIS: high_rpm (rpm={rpm:.0f})")
            
            # Low RPM in gear analysis
            if gear > 2 and rpm < 3000 and speed > 20 and can_trigger_situation('low_rpm_high_gear', 10.0):
                situations.append('low_rpm_high_gear')
                self._situation_cooldowns['low_rpm_high_gear'] = current_time
                logger.info(f"🚨 ANALYSIS: low_rpm_high_gear (gear={gear}, rpm={rpm:.0f})")
        
        # 7. COMBINED INPUT ANALYSIS - Advanced techniques
        if brake > 5 and throttle > 5 and can_trigger_situation('overlapping_inputs', 12.0):
            situations.append('overlapping_inputs')
            self._situation_cooldowns['overlapping_inputs'] = current_time
            logger.info(f"🚨 ANALYSIS: overlapping_inputs (brake={brake:.1f}%, throttle={throttle:.1f}%)")
        
        if brake > 10 and steering_magnitude > 8 and can_trigger_situation('trail_braking_attempt', 15.0):
            situations.append('trail_braking_attempt')
            self._situation_cooldowns['trail_braking_attempt'] = current_time
            logger.info(f"🚨 ANALYSIS: trail_braking_attempt (brake={brake:.1f}%, steering={steering:.1f}°)")
        
        # 8. PERFORMANCE ANALYSIS - Delta time based
        if delta_time and abs(delta_time) > 0.1:
            if delta_time > 1.0 and can_trigger_situation('losing_time', 15.0):
                situations.append('losing_time')
                self._situation_cooldowns['losing_time'] = current_time
                logger.info(f"🚨 ANALYSIS: losing_time (delta={delta_time:.2f}s)")
            
            elif delta_time > 0.3 and can_trigger_situation('slight_time_loss', 20.0):
                situations.append('slight_time_loss')
                self._situation_cooldowns['slight_time_loss'] = current_time
                logger.info(f"🚨 ANALYSIS: slight_time_loss (delta={delta_time:.2f}s)")
        
        # 9. FUEL & STRATEGY ANALYSIS
        if fuel < 25 and can_trigger_situation('fuel_management', 30.0):
            situations.append('fuel_management')
            self._situation_cooldowns['fuel_management'] = current_time
            logger.info(f"🚨 ANALYSIS: fuel_management (fuel={fuel:.1f}%)")
        
        # 10. CORNER ANALYSIS - Track position based
        if hasattr(self, '_last_lap_pct') and lap_pct != self._last_lap_pct:
            lap_pct_delta = abs(lap_pct - self._last_lap_pct)
            
            # Detect potential corners by steering and lap position
            if steering_magnitude > 5 and lap_pct_delta > 0.001 and can_trigger_situation('corner_analysis', 8.0):
                situations.append('corner_analysis')
                self._situation_cooldowns['corner_analysis'] = current_time
                logger.info(f"🚨 ANALYSIS: corner_analysis (steering={steering:.1f}°, lap_pct={lap_pct:.3f})")
        
        # 11. OVERALL DRIVING SMOOTHNESS
        if len(self._telemetry_history) >= 180:  # 3 seconds of data
            recent_data = self._telemetry_history[-180:]
            
            # Calculate overall input variance
            throttle_var = np.var([h['throttle'] for h in recent_data])
            brake_var = np.var([h['brake'] for h in recent_data])
            steering_var = np.var([h['steering'] for h in recent_data])
            
            total_variance = throttle_var + brake_var + steering_var
            if total_variance > 200 and can_trigger_situation('overall_inconsistency', 20.0):
                situations.append('overall_inconsistency')
                self._situation_cooldowns['overall_inconsistency'] = current_time
                logger.info(f"🚨 ANALYSIS: overall_inconsistency (total_var={total_variance:.1f})")
        
        # Store values for next comparison
        self._last_throttle = throttle
        self._last_brake = brake
        self._last_steering = steering
        self._last_lap_pct = lap_pct
        
        return situations
    
    def _generate_llm_coaching_for_situation(self, telemetry: Dict[str, Any], situation: str) -> Optional[CoachingMessage]:
        """Generate LLM coaching message for a specific driving situation"""
        if not self.llm_enabled or not self.llm_api_key or self.llm_api_key == "your-openai-api-key-here":
            return None
        
        # Get enhanced context with track and car specifics
        enhanced_context = self._get_track_specific_context(telemetry, situation)
        
        # Generate LLM message with track-specific context
        llm_message = self._call_openai_llm_for_situation(enhanced_context, telemetry, situation)
        if llm_message:
            logger.info(f"🤖 LLM generated message for {situation}: '{llm_message}'")
            
            # Map situations to categories - EXPANDED for comprehensive analysis
            category_map = {
                # Braking analysis
                'panic_braking': 'braking',
                'heavy_braking': 'braking',
                'moderate_braking': 'braking',
                'inconsistent_braking': 'braking',
                
                # Throttle analysis
                'abrupt_throttle': 'throttle',
                'traction_risk': 'throttle',
                'jerky_throttle': 'throttle',
                
                # Steering & handling analysis
                'excessive_steering': 'handling',
                'high_speed_steering': 'handling',
                'unstable_steering': 'handling',
                
                # Racing line & track position
                'off_track_excursion': 'racing_line',
                
                # Speed management
                'inconsistent_speed': 'speed_management',
                'corner_too_fast': 'speed_management',
                'corner_too_slow': 'speed_management',
                
                # Gear & RPM
                'high_rpm': 'technique',
                'low_rpm_high_gear': 'technique',
                
                # Combined inputs
                'overlapping_inputs': 'technique',
                'trail_braking_attempt': 'technique',
                
                # Performance analysis
                'losing_time': 'performance',
                'slight_time_loss': 'performance',
                
                # Strategy
                'fuel_management': 'strategy',
                
                # Corner analysis
                'corner_analysis': 'racing_line',
                
                # Overall consistency
                'overall_inconsistency': 'general',
                
                # Legacy situations (keeping for compatibility)
                'aggressive_braking': 'braking',
                'sudden_throttle': 'throttle',
                'wheel_spin_risk': 'throttle',
                'understeer_risk': 'handling',
                'oversteer_risk': 'handling',
                'off_track': 'racing_line',
                'high_speed_section': 'speed_management',
                'slow_speed_section': 'speed_management',
                'trail_braking': 'technique',
                'low_fuel': 'strategy',
                'corner_approach': 'racing_line'
            }
            
            return CoachingMessage(
                message=llm_message,
                category=category_map.get(situation, 'general'),
                priority=6,  # High priority for LLM messages
                confidence=85.0,
                data_source=f"LLM_situation_{situation}",
                improvement_potential=0.1
            )
        
        return None
    
    def _call_openai_llm_for_situation(self, coaching_context: str, telemetry: Dict[str, float], situation: str) -> str:
        """Call OpenAI LLM to generate coaching message for a specific situation"""
        try:
            current_section = self._get_track_section(telemetry.get('lapDistPct', 0))
            speed = telemetry.get('speed', 0)
            throttle = telemetry.get('throttle', 0)
            brake = telemetry.get('brake', 0)
            steering = telemetry.get('steering', 0)
            gear = telemetry.get('gear', 1)
            rpm = telemetry.get('rpm', 0)
            fuel = telemetry.get('fuelLevel', 100)
            
            # Get dynamic track and car information
            track_name = telemetry.get('trackName', self.track_name or 'Unknown Track')
            car_name = telemetry.get('carName', self.car_name or 'GT3 Car')
            
            # Create comprehensive situation-specific prompts with track context
            situation_prompts = {
                # BRAKING ANALYSIS
                'panic_braking': f"Panic braking detected ({brake:.0f}% pressure) at {speed:.0f} mph on {track_name}. Help the driver brake more progressively and earlier.",
                'heavy_braking': f"Heavy braking ({brake:.0f}% pressure) at {speed:.0f} mph on {track_name}. Provide braking technique advice for this track section.",
                'moderate_braking': f"Moderate braking detected ({brake:.0f}% pressure) at {speed:.0f} mph on {track_name}. Analyze braking efficiency for this corner.",
                'inconsistent_braking': f"Inconsistent braking pattern detected on {track_name}. Help improve braking consistency and pressure modulation.",
                
                # THROTTLE ANALYSIS
                'abrupt_throttle': f"Abrupt throttle changes detected on {track_name} at {speed:.0f} mph. Provide advice on smoother throttle application.",
                'traction_risk': f"Traction risk detected ({throttle:.0f}% throttle at {speed:.0f} mph) on {track_name}. Advise on power delivery and grip management.",
                'jerky_throttle': f"Jerky throttle inputs detected on {track_name}. Help the driver develop smoother throttle control.",
                
                # STEERING & HANDLING ANALYSIS
                'excessive_steering': f"Excessive steering input ({steering:.0f}°) at {speed:.0f} mph on {track_name}. Provide advice on steering efficiency.",
                'high_speed_steering': f"Large steering input ({steering:.0f}°) at high speed ({speed:.0f} mph) on {track_name}. Analyze handling and stability.",
                'unstable_steering': f"Unstable steering detected on {track_name}. Help improve steering smoothness and car control.",
                
                # RACING LINE & TRACK POSITION
                'off_track_excursion': f"Off-track excursion detected at {speed:.0f} mph on {track_name}. Provide racing line guidance for this section.",
                
                # SPEED MANAGEMENT
                'inconsistent_speed': f"Inconsistent speed management detected on {track_name}. Help improve pace consistency through corners.",
                'corner_too_fast': f"Corner entry too fast ({speed:.0f} mph) on {track_name}. Provide advice on corner speed management.",
                'corner_too_slow': f"Corner speed too conservative ({speed:.0f} mph) on {track_name}. Help find more pace through this section.",
                
                # GEAR & RPM ANALYSIS
                'high_rpm': f"High RPM detected ({rpm:.0f} RPM) on {track_name}. Advise on gear selection and engine management.",
                'low_rpm_high_gear': f"Low RPM in high gear (gear {gear}, {rpm:.0f} RPM) on {track_name}. Provide gearing advice for this section.",
                
                # COMBINED INPUT ANALYSIS
                'overlapping_inputs': f"Overlapping brake/throttle inputs detected on {track_name}. Analyze technique and provide refinement advice.",
                'trail_braking_attempt': f"Trail braking attempt detected on {track_name}. Provide feedback on this advanced technique.",
                
                # PERFORMANCE ANALYSIS
                'losing_time': f"Significant time loss detected (+{telemetry.get('deltaTime', 0):.2f}s) on {track_name}. Identify key areas for improvement.",
                'slight_time_loss': f"Minor time loss detected (+{telemetry.get('deltaTime', 0):.2f}s) on {track_name}. Provide fine-tuning advice.",
                
                # STRATEGY
                'fuel_management': f"Fuel management situation ({fuel:.0f}% remaining) on {track_name}. Provide fuel-saving driving techniques.",
                
                # CORNER ANALYSIS
                'corner_analysis': f"Corner analysis: {steering:.0f}° steering at {speed:.0f} mph on {track_name}. Provide corner-specific optimization advice.",
                
                # OVERALL CONSISTENCY
                'overall_inconsistency': f"Overall driving inconsistency detected on {track_name}. Help improve smoothness across all inputs.",
                
                # LEGACY SITUATIONS (keeping for compatibility)
                'aggressive_braking': f"Aggressive braking detected ({brake:.0f}% pressure) at {speed:.0f} mph on {track_name}. Provide braking technique advice.",
                'sudden_throttle': f"Sudden throttle application detected on {track_name} at {speed:.0f} mph. Advise on smoother power delivery.",
                'wheel_spin_risk': f"Wheel spin risk detected ({throttle:.0f}% throttle at {speed:.0f} mph) on {track_name}. Provide traction management advice.",
                'understeer_risk': f"Potential understeer detected ({steering:.0f}°) at {speed:.0f} mph on {track_name}. Provide handling advice.",
                'oversteer_risk': f"Potential oversteer detected ({steering:.0f}°) at {speed:.0f} mph on {track_name}. Provide car control advice.",
                'off_track': f"Off-track detected at {speed:.0f} mph on {track_name}. Provide racing line guidance.",
                'high_speed_section': f"High speed section ({speed:.0f} mph) on {track_name}. Provide advice for this fast section.",
                'slow_speed_section': f"Technical section ({speed:.0f} mph) on {track_name}. Provide advice for this slow section.",
                'trail_braking': f"Trail braking detected on {track_name}. Provide feedback on this advanced technique.",
                'low_fuel': f"Low fuel situation on {track_name}. Provide fuel-saving driving advice.",
                'corner_approach': f"Corner approach on {track_name} with {steering:.0f}° steering at {speed:.0f} mph. Provide cornering advice."
            }
            
            base_prompt = situation_prompts.get(situation, f"Driving situation: {situation} on {track_name}")
            
            # Enhanced prompt with track knowledge
            prompt = f"""{base_prompt}

Current location: {current_section} on {track_name}
Car: {car_name}
Speed: {speed:.0f} mph
Throttle: {throttle:.0f}%
Brake: {brake:.0f}%
Steering: {steering:.0f}°

Use your knowledge of {track_name}'s specific layout, elevation changes, corner characteristics, and optimal racing lines. Consider:
- Track-specific braking points and turn-in points
- Elevation changes and how they affect car handling
- Track surface characteristics and grip levels
- Corner sequences and setup for following turns
- Track-specific racing lines and apex points

Give ONE specific, actionable coaching tip under 60 characters. Address the driver directly."""

            headers = {
                'Authorization': f'Bearer {self.llm_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.llm_model,
                'messages': [
                    {'role': 'system', 'content': 'You are a professional racing coach with deep knowledge of racing circuits worldwide. Give concise, track-specific coaching advice. Respond with only the coaching message.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 50,
                'temperature': 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result['choices'][0]['message']['content'].strip()
                
                # Clean up the message
                message = message.replace('"', '').replace("'", "")
                if message.endswith('.'):
                    message = message[:-1]
                
                logger.info(f"🤖 LLM generated message: {message}")
                return message
            else:
                logger.error(f"OpenAI API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None
