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
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict
from dataclasses import dataclass, field

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
            
            # Generate various coaching messages
            messages.extend(self._analyze_track_surface(telemetry))
            messages.extend(self._analyze_brake_usage(telemetry))
            messages.extend(self._analyze_throttle_application(telemetry))
            messages.extend(self._generate_general_tips(telemetry))
            
            if len(self.laps) >= 2:
                messages.extend(self._analyze_consistency(telemetry))
            
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
        
        if brake_pressure > 80 and speed > 100:
            if not hasattr(self, '_last_hard_brake') or time.time() - self._last_hard_brake > 5:
                messages.append(CoachingMessage(
                    message="Heavy braking detected - try progressive braking",
                    category="braking",
                    priority=4,
                    confidence=70,
                    data_source="brake_pressure"
                ))
                self._last_hard_brake = time.time()
        
        return messages
    
    def _analyze_throttle_application(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze throttle usage"""
        messages = []
        throttle = telemetry.get('throttle', 0)
        speed = telemetry.get('speed', 0)
        
        if throttle > 95 and speed < 60:
            messages.append(CoachingMessage(
                message="Gradual throttle buildup recommended at low speeds",
                category="throttle",
                priority=4,
                confidence=70,
                data_source="throttle_speed"
            ))
        
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
    
    def _generate_general_tips(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Generate general coaching tips"""
        messages = []
        current_time = time.time()
        
        tips = [
            "Focus on smooth inputs - consistency beats speed",
            "Look ahead - where you look is where you'll go",
            "Exit speed matters more than entry speed",
            "Smooth inputs lead to faster lap times"
        ]
        
        # Only add tip occasionally to avoid spam
        if len(messages) == 0 and current_time % 10 < 1:  # Every ~10 seconds
            selected_tip = random.choice(tips)
            if selected_tip not in self.recent_messages or \
               current_time - self.recent_messages[selected_tip] > self.message_cooldown:
                messages.append(CoachingMessage(
                    message=selected_tip,
                    category="tip",
                    priority=2,
                    confidence=85,
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
