#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local AI Coaching Engine for GT3 Racing
Provides real-time driving analysis and coaching feedback
"""

import numpy as np
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from collections import deque, defaultdict
from dataclasses import dataclass, field
import json
import sys
import io

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    # Set default encoding for stdout/stderr
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        # Fallback for older Python versions
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
    brake_events: List[Dict] = field(default_factory=list)
    throttle_events: List[Dict] = field(default_factory=list)
    tire_temps: Dict[str, float] = field(default_factory=dict)
    brake_temps: Dict[str, float] = field(default_factory=dict)
    fuel_used: float = 0.0
    incidents: int = 0
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
    """Local AI coaching system that learns from your driving"""
    
    def __init__(self):
        self.laps: List[LapData] = []
        self.current_lap_data = {}
        self.best_lap: Optional[LapData] = None
        self.baseline_established = False
        self.session_start_time = time.time()
        
        # AI Learning Parameters
        self.brake_point_history = defaultdict(list)  # corner_id -> [brake_points]
        self.speed_history = defaultdict(list)        # sector_id -> [speeds]
        self.consistency_threshold = 0.05  # 5% variance for consistency
        self.learning_rate = 0.1
        
        # Real-time telemetry buffer (last 60 seconds at 60Hz = 3600 samples)
        self.telemetry_buffer = deque(maxlen=3600)
        self.current_sector = 0
        self.last_brake_point = None
        self.last_throttle_point = None
        
        # Performance baselines (updated as driver improves)
        self.target_tire_temps = {'LF': 220, 'RF': 220, 'LR': 200, 'RR': 200}  # Fahrenheit
        self.target_brake_temps = {'LF': 400, 'RF': 400, 'LR': 350, 'RR': 350}  # Fahrenheit
        
        # Advanced learning attributes
        self.driving_style = "unknown"  # consistent, developing, improving
        self.coaching_intensity = 1.0   # Adaptive coaching intensity
        self.track_learning = {}        # Track-specific learned patterns
        
        # Message deduplication system
        self.recent_messages = {}  # message_text -> timestamp
        self.message_cooldown = 8.0  # Seconds before same message can be sent again
        
        logger.info("🤖 Local AI Coach initialized - ready to learn your driving style")
    
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
            
            # Immediate feedback (works from lap 1)
            messages.extend(self._analyze_tire_management(telemetry))
            messages.extend(self._analyze_brake_usage(telemetry))
            messages.extend(self._analyze_throttle_application(telemetry))
            
            # Advanced feedback (requires lap history)
            if len(self.laps) >= 2:
                messages.extend(self._analyze_consistency(telemetry))
                messages.extend(self._analyze_racing_line(telemetry))
                messages.extend(self._analyze_sector_performance(telemetry))
            
            # Filter and prioritize messages
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
            'gear': telemetry.get('gear', 0),
            'rpm': telemetry.get('rpm', 0),
            'tire_temps': {
                'LF': telemetry.get('tireTempLF', 0),
                'RF': telemetry.get('tireTempRF', 0),
                'LR': telemetry.get('tireTempLR', 0),
                'RR': telemetry.get('tireTempRR', 0)
            },
            'brake_temps': {
                'LF': telemetry.get('brakeTempLF', 0),
                'RF': telemetry.get('brakeTempRF', 0),
                'LR': telemetry.get('brakeTempLR', 0),
                'RR': telemetry.get('brakeTempRR', 0)
            }
        })
    
    def _complete_lap(self):
        """Process completed lap and update AI models"""
        if not self.current_lap_data:
            return
        
        try:
            # Create lap data object
            lap_time = self.current_lap_data.get('current_lap_time', 0)
            if lap_time <= 0:
                return  # Invalid lap
            
            lap = LapData(
                lap_number=self.current_lap_data.get('lap_number', 0),
                lap_time=lap_time,
                tire_temps=self.current_lap_data.get('tire_temps', {}),
                brake_temps=self.current_lap_data.get('brake_temps', {})
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
                logger.info("📊 AI baseline established - advanced coaching now available")
            
            # Learn from this lap
            self._update_ai_models(lap)
            
        except Exception as e:
            logger.error(f"Error completing lap: {e}")
    
    def _establish_baseline(self):
        """Establish performance baseline from first few laps"""
        if len(self.laps) < 3:
            return
        
        # Calculate average performance metrics
        lap_times = [lap.lap_time for lap in self.laps if lap.lap_time > 0]
        if lap_times:
            avg_lap_time = np.mean(lap_times)
            std_lap_time = np.std(lap_times)
            
            # Update consistency threshold based on driver's natural variation
            self.consistency_threshold = max(0.02, min(0.1, std_lap_time / avg_lap_time))
            
            logger.info(f"📈 Baseline: Avg lap {avg_lap_time:.3f}s, consistency {self.consistency_threshold:.1%}")
    
    def _update_ai_models(self, lap: LapData):
        """Update AI learning models with new lap data"""
        try:
            # 1. Learn optimal tire temperature management
            self._learn_tire_management(lap)
            
            # 2. Analyze and learn from brake patterns
            self._learn_brake_patterns(lap)
            
            # 3. Update driving style classification
            self._classify_driving_style(lap)
            
            # 4. Learn track-specific patterns (if we have position data)
            self._learn_track_patterns(lap)
            
            # 5. Adaptive threshold updates
            self._update_adaptive_thresholds(lap)
            
            logger.debug(f"🧠 AI models updated with lap {lap.lap_number} data")
            
        except Exception as e:
            logger.error(f"Error updating AI models: {e}")
    
    def _learn_tire_management(self, lap: LapData):
        """Learn optimal tire temperature patterns from successful laps"""
        if not lap.tire_temps or lap.lap_time <= 0:
            return
            
        # Only learn from good laps (within 102% of best time)
        if self.best_lap and lap.lap_time > self.best_lap.lap_time * 1.02:
            return
            
        # Update optimal temperature targets based on fast laps
        for tire, temp in lap.tire_temps.items():
            if temp > 0:  # Valid temperature
                current_target = self.target_tire_temps[tire]
                
                # Exponential moving average to learn optimal temps
                alpha = self.learning_rate
                self.target_tire_temps[tire] = (1 - alpha) * current_target + alpha * temp
                
        logger.debug(f"🌡️ Updated tire targets: {self.target_tire_temps}")
    
    def _learn_brake_patterns(self, lap: LapData):
        """Learn optimal brake temperature patterns"""
        if not lap.brake_temps or lap.lap_time <= 0:
            return
            
        # Only learn from good laps
        if self.best_lap and lap.lap_time > self.best_lap.lap_time * 1.02:
            return
            
        # Update optimal brake temperature targets
        for brake, temp in lap.brake_temps.items():
            if temp > 0:  # Valid temperature
                current_target = self.target_brake_temps[brake]
                
                # Learn optimal brake temps (cooler is generally better for consistency)
                alpha = self.learning_rate * 0.5  # Learn slower for brakes
                self.target_brake_temps[brake] = (1 - alpha) * current_target + alpha * temp
                
        logger.debug(f"🔥 Updated brake targets: {self.target_brake_temps}")
    
    def _classify_driving_style(self, lap: LapData):
        """Classify and adapt to driver's style"""
        if len(self.laps) < 5:
            return
            
        # Analyze recent consistency
        recent_times = [l.lap_time for l in self.laps[-5:] if l.lap_time > 0]
        if len(recent_times) < 3:
            return
            
        consistency = np.std(recent_times) / np.mean(recent_times)
        
        # Classify driving style and adapt coaching
        if consistency < 0.01:  # Very consistent (< 1% variation)
            self.driving_style = "consistent"
            self.coaching_intensity = 0.7  # Less aggressive coaching
        elif consistency > 0.05:  # Inconsistent (> 5% variation)
            self.driving_style = "developing"
            self.coaching_intensity = 1.2  # More guidance needed
        else:
            self.driving_style = "improving"
            self.coaching_intensity = 1.0  # Standard coaching
            
        logger.debug(f"🎯 Driving style: {getattr(self, 'driving_style', 'unknown')}, intensity: {getattr(self, 'coaching_intensity', 1.0)}")
    
    def _learn_track_patterns(self, lap: LapData):
        """Learn track-specific patterns (placeholder for future enhancement)"""
        # This would analyze racing line, speed patterns, etc.
        # For now, just store lap time patterns
        if hasattr(self, 'track_learning'):
            self.track_learning['lap_times'].append(lap.lap_time)
        else:
            self.track_learning = {'lap_times': [lap.lap_time]}
            
        # Keep only recent data (last 20 laps)
        if len(self.track_learning['lap_times']) > 20:
            self.track_learning['lap_times'] = self.track_learning['lap_times'][-20:]
    
    def _update_adaptive_thresholds(self, lap: LapData):
        """Update coaching thresholds based on driver improvement"""
        if len(self.laps) < 10:
            return
            
        # Get recent performance trend
        recent_laps = self.laps[-10:]
        recent_times = [l.lap_time for l in recent_laps if l.lap_time > 0]
        
        if len(recent_times) < 5:
            return
            
        # Calculate improvement trend
        first_half = np.mean(recent_times[:len(recent_times)//2])
        second_half = np.mean(recent_times[len(recent_times)//2:])
        improvement_rate = (first_half - second_half) / first_half
        
        # Adapt thresholds based on improvement
        if improvement_rate > 0.02:  # Improving fast (>2%)
            self.consistency_threshold *= 0.95  # Tighten standards
            logger.info("🚀 Driver improving rapidly - raising coaching standards")
        elif improvement_rate < -0.01:  # Getting slower
            self.consistency_threshold *= 1.05  # Be more forgiving
            logger.info("📉 Performance declining - adjusting coaching approach")
    
    def _analyze_tire_management(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze tire temperatures and provide management advice"""
        messages = []
        
        tire_temps = {
            'LF': telemetry.get('tireTempLF', 0),
            'RF': telemetry.get('tireTempRF', 0),
            'LR': telemetry.get('tireTempLR', 0),
            'RR': telemetry.get('tireTempRR', 0)
        }
        
        # Apply coaching intensity modifier
        intensity = getattr(self, 'coaching_intensity', 1.0)
        
        # Check for overheating
        for tire, temp in tire_temps.items():
            if temp > 0:  # Valid temperature
                target = self.target_tire_temps[tire]
                
                if temp > target + (30 / intensity):  # Adaptive threshold
                    messages.append(CoachingMessage(
                        message=f"{tire} tire overheating ({temp:.0f}F) - ease off the pace",
                        category="tires",
                        priority=min(10, int(8 * intensity)),
                        confidence=90,
                        data_source="tire_temp",
                        improvement_potential=0.5
                    ))
                elif temp > target + (15 / intensity):  # Getting hot
                    messages.append(CoachingMessage(
                        message=f"{tire} tire getting hot ({temp:.0f}F) - manage pace",
                        category="tires",
                        priority=min(10, int(5 * intensity)),
                        confidence=85,
                        data_source="tire_temp"
                    ))
                elif temp < target - 20:  # Too cold
                    messages.append(CoachingMessage(
                        message=f"{tire} tire cold ({temp:.0f}F) - push harder to warm up",
                        category="tires",
                        priority=4,
                        confidence=80,
                        data_source="tire_temp"
                    ))
        
        # Check tire balance with learned targets
        if all(temp > 0 for temp in tire_temps.values()):
            front_avg = (tire_temps['LF'] + tire_temps['RF']) / 2
            rear_avg = (tire_temps['LR'] + tire_temps['RR']) / 2
            
            # Use learned optimal balance
            learned_front_avg = (self.target_tire_temps['LF'] + self.target_tire_temps['RF']) / 2
            learned_rear_avg = (self.target_tire_temps['LR'] + self.target_tire_temps['RR']) / 2
            learned_balance = learned_front_avg - learned_rear_avg
            current_balance = front_avg - rear_avg
            
            if abs(current_balance - learned_balance) > 15:
                if current_balance > learned_balance:
                    messages.append(CoachingMessage(
                        message="Front tires running hotter than your optimal balance - adjust driving style",
                        category="tires",
                        priority=6,
                        confidence=80,
                        data_source="tire_balance_learned"
                    ))
                else:
                    messages.append(CoachingMessage(
                        message="Rear tires running hotter than your optimal balance - check setup",
                        category="tires",
                        priority=6,
                        confidence=80,
                        data_source="tire_balance_learned"
                    ))
        
        return messages
    
    def _analyze_brake_usage(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze braking patterns and temperatures"""
        messages = []
        
        brake_pressure = telemetry.get('brake', 0)
        speed = telemetry.get('speed', 0)
        
        # Check brake temperatures
        brake_temps = {
            'LF': telemetry.get('brakeTempLF', 0),
            'RF': telemetry.get('brakeTempRF', 0),
            'LR': telemetry.get('brakeTempLR', 0),
            'RR': telemetry.get('brakeTempRR', 0)
        }
        
        for brake, temp in brake_temps.items():
            if temp > 0:  # Valid temperature
                target = self.target_brake_temps[brake]
                
                if temp > target + 100:  # Overheating
                    messages.append(CoachingMessage(
                        message=f"{brake} brake overheating ({temp:.0f}F) - brake earlier and lighter",
                        category="braking",
                        priority=9,
                        confidence=95,
                        data_source="brake_temp",
                        improvement_potential=0.3
                    ))
                elif temp > target + 50:  # Getting hot
                    messages.append(CoachingMessage(
                        message=f"{brake} brake getting hot ({temp:.0f}F) - ease brake pressure",
                        category="braking",
                        priority=6,
                        confidence=85,
                        data_source="brake_temp"
                    ))
        
        # Analyze braking technique
        if brake_pressure > 80 and speed > 100:  # Hard braking at high speed
            if not hasattr(self, '_last_hard_brake') or time.time() - self._last_hard_brake > 5:
                messages.append(CoachingMessage(
                    message="Heavy braking detected - try progressive braking for better tire wear",
                    category="braking",
                    priority=4,
                    confidence=70,
                    data_source="brake_pressure"
                ))
                self._last_hard_brake = time.time()
        
        return messages
    
    def _analyze_throttle_application(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze throttle usage patterns"""
        messages = []
        
        throttle = telemetry.get('throttle', 0)
        speed = telemetry.get('speed', 0)
        gear = telemetry.get('gear', 0)
        
        # Check for aggressive throttle application
        if len(self.telemetry_buffer) >= 2:
            prev_throttle = self.telemetry_buffer[-2].get('throttle', 0)
            throttle_delta = throttle - prev_throttle
            
            # Sudden throttle spike (potential for wheelspin)
            if throttle_delta > 30 and speed < 80 and gear > 1:  # Quick throttle at low speed
                messages.append(CoachingMessage(
                    message="Smooth throttle application - avoid sudden inputs for better traction",
                    category="throttle",
                    priority=5,
                    confidence=75,
                    data_source="throttle_delta"
                ))
        
        # Check for full throttle at low speed (wheelspin risk)
        if throttle > 95 and speed < 60 and gear > 1:
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
        
        # Get recent lap times
        recent_laps = self.laps[-5:]  # Last 5 laps
        lap_times = [lap.lap_time for lap in recent_laps if lap.lap_time > 0]
        
        if len(lap_times) >= 3:
            avg_time = np.mean(lap_times)
            std_time = np.std(lap_times)
            consistency = std_time / avg_time if avg_time > 0 else 0
            
            if consistency > self.consistency_threshold * 2:  # Poor consistency
                messages.append(CoachingMessage(
                    message=f"Focus on consistency - lap times varying by {std_time:.3f}s",
                    category="general",
                    priority=7,
                    confidence=80,
                    data_source="lap_times",
                    improvement_potential=std_time * 0.5
                ))
            elif consistency < self.consistency_threshold * 0.5:  # Very consistent
                messages.append(CoachingMessage(
                    message="Excellent consistency! Time to push for pace",
                    category="general",
                    priority=3,
                    confidence=90,
                    data_source="lap_times"
                ))
        
        return messages
    
    def _analyze_racing_line(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze racing line efficiency"""
        messages = []
        
        # This would be more sophisticated with actual track mapping
        # For now, basic speed-based analysis
        speed = telemetry.get('speed', 0)
        throttle = telemetry.get('throttle', 0)
        brake = telemetry.get('brake', 0)
        
        # Look for simultaneous brake and throttle (inefficient)
        if brake > 10 and throttle > 10:
            messages.append(CoachingMessage(
                message="Avoid overlapping brake and throttle - pick one input at a time",
                category="racing_line",
                priority=6,
                confidence=85,
                data_source="input_overlap"
            ))
        
        return messages
    
    def _analyze_sector_performance(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze sector-by-sector performance"""
        messages = []
        
        # This would require sector timing data from iRacing
        # For now, basic analysis
        
        if self.best_lap and len(self.laps) >= 5:
            current_lap_time = telemetry.get('lapCurrentLapTime', 0)
            best_time = self.best_lap.lap_time
            
            if current_lap_time > best_time * 1.05:  # More than 5% slower
                messages.append(CoachingMessage(
                    message=f"Current lap {(current_lap_time - best_time):.3f}s slower than best",
                    category="general",
                    priority=5,
                    confidence=90,
                    data_source="lap_comparison"
                ))
        
        return messages
    
    def _prioritize_messages(self, messages: List[CoachingMessage]) -> List[CoachingMessage]:
        """Filter and prioritize coaching messages with deduplication"""
        current_time = time.time()
        
        # Clean up old messages from deduplication cache
        expired_messages = [msg for msg, timestamp in self.recent_messages.items() 
                          if current_time - timestamp > self.message_cooldown]
        for msg in expired_messages:
            del self.recent_messages[msg]
        
        # Filter out duplicate messages
        filtered_messages = []
        for message in messages:
            if message.message not in self.recent_messages:
                filtered_messages.append(message)
                # Add to recent messages cache
                self.recent_messages[message.message] = current_time
            else:
                # Check if it's a high priority message that should override cooldown
                time_since_last = current_time - self.recent_messages[message.message]
                if message.priority >= 8 and time_since_last > (self.message_cooldown / 2):
                    # Allow critical messages to appear more frequently
                    filtered_messages.append(message)
                    self.recent_messages[message.message] = current_time
        
        if not filtered_messages:
            # Return a default message if all messages were filtered out as duplicates
            default_msg = "All systems looking good - keep it up!"
            if default_msg not in self.recent_messages or \
               current_time - self.recent_messages[default_msg] > self.message_cooldown * 2:
                self.recent_messages[default_msg] = current_time
                return [CoachingMessage(
                    message=default_msg,
                    category="general",
                    priority=2,
                    confidence=80,
                    data_source="default"
                )]
            else:
                return []  # Return empty if even default message is on cooldown
        
        # Sort by priority (higher first)
        filtered_messages.sort(key=lambda x: x.priority, reverse=True)
        
        # Return top 3 most important messages
        return filtered_messages[:3]
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get AI analysis summary for the session"""
        if not self.laps:
            return {"message": "No laps completed yet"}
        
        summary = {
            "laps_completed": len(self.laps),
            "best_lap_time": self.best_lap.lap_time if self.best_lap else None,
            "best_lap_number": self.best_lap.lap_number if self.best_lap else None,
            "session_duration": time.time() - self.session_start_time,
            "baseline_established": self.baseline_established,
            
            # AI Learning Insights
            "driving_style": getattr(self, 'driving_style', 'unknown'),
            "coaching_intensity": getattr(self, 'coaching_intensity', 1.0),
            "learned_tire_temps": self.target_tire_temps,
            "learned_brake_temps": self.target_brake_temps
        }
        
        if len(self.laps) >= 3:
            lap_times = [lap.lap_time for lap in self.laps if lap.lap_time > 0]
            summary.update({
                "average_lap_time": np.mean(lap_times),
                "consistency": np.std(lap_times) / np.mean(lap_times) if lap_times else 0,
                "improvement": (max(lap_times) - min(lap_times)) if len(lap_times) > 1 else 0,
                
                # Performance trend analysis
                "recent_trend": self._calculate_improvement_trend(lap_times)
            })
        
        return summary
    
    def _calculate_improvement_trend(self, lap_times: List[float]) -> str:
        """Calculate if driver is improving, stable, or declining"""
        if len(lap_times) < 6:
            return "insufficient_data"
            
        # Compare first third vs last third of session
        third = len(lap_times) // 3
        early_avg = np.mean(lap_times[:third])
        late_avg = np.mean(lap_times[-third:])
        
        improvement = (early_avg - late_avg) / early_avg
        
        if improvement > 0.02:  # More than 2% improvement
            return "improving_fast"
        elif improvement > 0.005:  # More than 0.5% improvement
            return "improving"
        elif improvement > -0.005:  # Within 0.5%
            return "stable"
        else:
            return "declining"
