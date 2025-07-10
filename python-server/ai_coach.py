#!/usr/bin/env python3
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
        # This is where machine learning would happen in a full implementation
        # For now, we'll do statistical learning
        pass
    
    def _analyze_tire_management(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze tire temperatures and provide management advice"""
        messages = []
        
        tire_temps = {
            'LF': telemetry.get('tireTempLF', 0),
            'RF': telemetry.get('tireTempRF', 0),
            'LR': telemetry.get('tireTempLR', 0),
            'RR': telemetry.get('tireTempRR', 0)
        }
        
        # Check for overheating
        for tire, temp in tire_temps.items():
            if temp > 0:  # Valid temperature
                target = self.target_tire_temps[tire]
                
                if temp > target + 30:  # Overheating
                    messages.append(CoachingMessage(
                        message=f"{tire} tire overheating ({temp:.0f}°F) - ease off the pace",
                        category="tires",
                        priority=8,
                        confidence=90,
                        data_source="tire_temp",
                        improvement_potential=0.5
                    ))
                elif temp > target + 15:  # Getting hot
                    messages.append(CoachingMessage(
                        message=f"{tire} tire getting hot ({temp:.0f}°F) - manage pace",
                        category="tires",
                        priority=5,
                        confidence=85,
                        data_source="tire_temp"
                    ))
                elif temp < target - 20:  # Too cold
                    messages.append(CoachingMessage(
                        message=f"{tire} tire cold ({temp:.0f}°F) - push harder to warm up",
                        category="tires",
                        priority=4,
                        confidence=80,
                        data_source="tire_temp"
                    ))
        
        # Check tire balance
        if all(temp > 0 for temp in tire_temps.values()):
            front_avg = (tire_temps['LF'] + tire_temps['RF']) / 2
            rear_avg = (tire_temps['LR'] + tire_temps['RR']) / 2
            
            if front_avg > rear_avg + 20:
                messages.append(CoachingMessage(
                    message="Front tires much hotter than rear - check setup or driving style",
                    category="tires",
                    priority=6,
                    confidence=75,
                    data_source="tire_balance"
                ))
            elif rear_avg > front_avg + 20:
                messages.append(CoachingMessage(
                    message="Rear tires much hotter than front - possible oversteer or setup issue",
                    category="tires",
                    priority=6,
                    confidence=75,
                    data_source="tire_balance"
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
                        message=f"{brake} brake overheating ({temp:.0f}°F) - brake earlier and lighter",
                        category="braking",
                        priority=9,
                        confidence=95,
                        data_source="brake_temp",
                        improvement_potential=0.3
                    ))
                elif temp > target + 50:  # Getting hot
                    messages.append(CoachingMessage(
                        message=f"{brake} brake getting hot ({temp:.0f}°F) - ease brake pressure",
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
        """Filter and prioritize coaching messages"""
        if not messages:
            return [CoachingMessage(
                message="All systems looking good - keep it up!",
                category="general",
                priority=2,
                confidence=80,
                data_source="default"
            )]
        
        # Sort by priority (higher first)
        messages.sort(key=lambda x: x.priority, reverse=True)
        
        # Return top 3 most important messages
        return messages[:3]
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get AI analysis summary for the session"""
        if not self.laps:
            return {"message": "No laps completed yet"}
        
        summary = {
            "laps_completed": len(self.laps),
            "best_lap_time": self.best_lap.lap_time if self.best_lap else None,
            "best_lap_number": self.best_lap.lap_number if self.best_lap else None,
            "session_duration": time.time() - self.session_start_time,
            "baseline_established": self.baseline_established
        }
        
        if len(self.laps) >= 3:
            lap_times = [lap.lap_time for lap in self.laps if lap.lap_time > 0]
            summary.update({
                "average_lap_time": np.mean(lap_times),
                "consistency": np.std(lap_times) / np.mean(lap_times) if lap_times else 0,
                "improvement": (max(lap_times) - min(lap_times)) if len(lap_times) > 1 else 0
            })
        
        return summary
