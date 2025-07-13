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
        """Process incoming telemetry and generate coaching messages"""
        try:
            # Add to telemetry buffer
            telemetry['timestamp'] = time.time()
            self.telemetry_buffer.append(telemetry.copy())
            
            # Update current lap data
            self._update_current_lap_data(telemetry)
            
            # Generate coaching messages
            messages = []
            
            # If baseline not established, only show countdown message
            if not self.baseline_established:
                countdown_message = self._generate_baseline_countdown(telemetry)
                if countdown_message:
                    messages.append(countdown_message)
                return self._prioritize_messages(messages)
            
            # Generate various coaching messages with progressive focus
            messages.extend(self._analyze_track_surface(telemetry))
            messages.extend(self._analyze_brake_usage(telemetry))
            messages.extend(self._analyze_throttle_application(telemetry))
            messages.extend(self._analyze_speed_management(telemetry))
            messages.extend(self._analyze_driving_rhythm(telemetry))
            messages.extend(self._analyze_sector_performance(telemetry))
            messages.extend(self._analyze_situational_awareness(telemetry))
            
            # LLM coaching (if enabled)
            messages.extend(self._generate_llm_coaching(telemetry))
            
            messages.extend(self._generate_progressive_coaching(telemetry))
            messages.extend(self._generate_general_tips(telemetry))
            
            if len(self.laps) >= 2:
                messages.extend(self._analyze_consistency(telemetry))
            
            # LLM Coaching
            messages.extend(self._generate_llm_coaching(telemetry))
            
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
        speed = telemetry.get('speed', 0)
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
        
        # Heavy braking detection (much lower threshold for more frequent coaching)
        if brake_pressure > 40 and speed > 40:  # Lowered from 60% brake and 60mph
            if not hasattr(self, '_last_hard_brake') or current_time - self._last_hard_brake > 6:
                messages.append(CoachingMessage(
                    message="Heavy braking - try progressive braking for smoother cornering",
                    category="braking",
                    priority=5,
                    confidence=75,
                    data_source="brake_pressure"
                ))
                self._last_hard_brake = current_time
        
        # Trail braking detection (much lower threshold)
        if brake_pressure > 10 and throttle > 5:  # Both brake and throttle active
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
            if brake_delta > 25 and speed > 30:  # Sudden brake release
                if not hasattr(self, '_last_brake_release') or current_time - self._last_brake_release > 8:
                    messages.append(CoachingMessage(
                        message="Smooth brake release helps maintain car balance through corners",
                        category="braking",
                        priority=4,
                        confidence=65,
                        data_source="brake_release"
                    ))
                    self._last_brake_release = current_time
        
        # Brake lockup prevention (new lower threshold)
        if brake_pressure > 70 and speed > 80:
            if not hasattr(self, '_last_lockup_warning') or current_time - self._last_lockup_warning > 10:
                messages.append(CoachingMessage(
                    message="High brake pressure at speed - watch for lockups and find the limit",
                    category="braking",
                    priority=6,
                    confidence=80,
                    data_source="lockup_prevention"
                ))
                self._last_lockup_warning = current_time
        
        self._last_brake_pressure = brake_pressure
        return messages
    
    def _analyze_throttle_application(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze throttle usage patterns"""
        messages = []
        throttle = telemetry.get('throttle', 0)
        speed = telemetry.get('speed', 0)
        gear = telemetry.get('gear', 0)
        
        current_time = time.time()
        
        # Aggressive throttle application (much lower threshold)
        if hasattr(self, '_last_throttle'):
            throttle_delta = throttle - self._last_throttle
            if throttle_delta > 20 and speed > 20:  # Sudden throttle increase
                if not hasattr(self, '_last_aggressive_throttle') or current_time - self._last_aggressive_throttle > 6:
                    messages.append(CoachingMessage(
                        message="Sudden throttle input - smooth application maintains traction",
                        category="throttle",
                        priority=4,
                        confidence=70,
                        data_source="throttle_application"
                    ))
                    self._last_aggressive_throttle = current_time
        
        # Full throttle at low speed (much lower threshold for wheel spin)
        if throttle > 70 and speed < 40 and gear > 1:
            if not hasattr(self, '_last_wheel_spin') or current_time - self._last_wheel_spin > 6:
                messages.append(CoachingMessage(
                    message="High throttle at low speed - build up gradually to avoid wheelspin",
                    category="throttle",
                    priority=6,
                    confidence=80,
                    data_source="wheel_spin_risk"
                ))
                self._last_wheel_spin = current_time
        
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
        steering_angle = abs(telemetry.get('steerAngle', 0))  # Get steering input for over/understeer detection
        
        current_time = time.time()
        
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
        
        # Oversteer detection (high steering with throttle application)
        if steering_angle > 12 and throttle > 50 and speed > 25:
            if not hasattr(self, '_last_oversteer') or current_time - self._last_oversteer > 8:
                messages.append(CoachingMessage(
                    message="High steering angle under throttle - possible oversteer, ease off throttle",
                    category="technique",
                    priority=6,
                    confidence=80,
                    data_source="oversteer_detection"
                ))
                self._last_oversteer = current_time
        
        # Understeer detection (excessive steering input)
        if steering_angle > 25 and speed > 50:
            if not hasattr(self, '_last_understeer') or current_time - self._last_understeer > 10:
                messages.append(CoachingMessage(
                    message="High steering angle - if car isn't turning, reduce speed into corner",
                    category="technique",
                    priority=5,
                    confidence=70,
                    data_source="understeer_detection"
                ))
                self._last_understeer = current_time
        
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
        """Generate natural language coaching using LLM"""
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
        
        # Detect coaching situation
        coaching_context = self._detect_coaching_moments(telemetry)
        if not coaching_context:
            return []
        
        # Log current telemetry for debugging
        speed = telemetry.get('Speed', 0)
        logger.info(f"🤖 LLM coaching triggered for: {coaching_context}")
        logger.info(f"   📊 Telemetry: Speed={speed:.1f}, Brake={telemetry.get('Brake', 0):.2f}, Throttle={telemetry.get('Throttle', 0):.2f}, Steering={telemetry.get('SteeringWheelAngle', 0):.2f}")
        
        # Generate LLM message
        llm_message = self._call_openai_llm(coaching_context, telemetry)
        if llm_message:
            self.last_llm_message = current_time
            logger.info(f"🤖 Generated LLM message: '{llm_message}'")
            return [CoachingMessage(
                message=llm_message,
                category="llm",
                priority=5,
                confidence=80.0,
                data_source="LLM_contextual_analysis",
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
        """Call OpenAI LLM to generate coaching message"""
        try:
            current_section = self._get_track_section(telemetry.get('LapDistPct', 0))
            speed = telemetry.get('Speed', 0) * 2.237  # Convert to MPH
            throttle = telemetry.get('Throttle', 0) * 100
            brake = telemetry.get('Brake', 0) * 100
            
            prompt = f"""You are an expert racing coach for GT3 cars. Based on the telemetry data, give ONE brief, specific coaching tip in a natural conversational tone.

Current situation: {coaching_context}
Track section: {current_section}
Speed: {speed:.0f} mph
Throttle: {throttle:.0f}%
Brake: {brake:.0f}%

Respond with just the coaching message, like:
- "Brake earlier going into Turn 1"
- "You're accelerating too hard coming out of that corner"
- "Ease off the throttle through the chicane"
- "Try a later braking point there"

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
