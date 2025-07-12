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
    # Note: tire_temps and brake_temps removed - iRacing doesn't provide reliable data during racing
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
        self.baseline_just_established = False  # Flag for showing congratulatory message
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
        
        # Track-specific coaching infrastructure
        self.track_map = {}  # lapDistPct -> corner/zone info
        self.corner_analysis = defaultdict(lambda: {
            'brake_points': [],
            'entry_speeds': [],
            'exit_speeds': [],
            'best_brake_point': None,
            'best_entry_speed': None,
            'consistent_times': []
        })
        self.current_corner = None
        self.in_braking_zone = False
        self.corner_names = self._initialize_corner_names()  # Track-specific corner names
        
        # Vehicle dynamics analysis for oversteer/understeer detection
        self.steering_response_history = deque(maxlen=300)  # 5 seconds at 60Hz
        self.understeer_events = defaultdict(list)  # corner -> understeer incidents
        self.oversteer_events = defaultdict(list)   # corner -> oversteer incidents
        self.last_handling_feedback = 0  # Throttle feedback timing
        
        # Handling analysis thresholds
        self.understeer_threshold = 0.7  # Steering vs response ratio
        self.oversteer_threshold = 0.3   # Lateral acceleration vs steering ratio
        
        # Performance baselines (updated as driver improves)
        # Note: Tire and brake temps removed as iRacing doesn't provide reliable data during racing
        
        # Advanced learning attributes
        self.driving_style = "unknown"  # consistent, developing, improving
        self.coaching_intensity = 1.0   # Adaptive coaching intensity
        self.track_learning = {}        # Track-specific learned patterns
        
        # Message deduplication system
        self.recent_messages = {}  # message_text -> timestamp
        self.message_cooldown = 3.0  # Seconds before same message can be sent again
        
        logger.info("🤖 Local AI Coach initialized - ready to learn your driving style")
    
    def _initialize_corner_names(self) -> Dict[float, str]:
        """Initialize track-specific corner names based on lap distance percentage"""
        # Generic corner map - can be enhanced for specific tracks
        # This maps lapDistPct ranges to corner names
        return {
            # Approximate corner positions (can be refined per track)
            0.05: "Turn 1",
            0.15: "Turn 2", 
            0.25: "Turn 3",
            0.35: "Turn 4",
            0.45: "Turn 5",
            0.55: "Turn 6",
            0.65: "Turn 7",
            0.75: "Turn 8",
            0.85: "Turn 9",
            0.95: "Turn 10"
        }
    
    def _identify_corner_from_position(self, lap_dist_pct: float) -> Optional[str]:
        """Identify which corner we're approaching based on track position"""
        if not self.corner_names:
            return None
            
        # Find the closest corner to current position
        closest_corner = None
        min_distance = float('inf')
        
        for corner_pos, corner_name in self.corner_names.items():
            # Handle track wrapping (0.95 to 0.05)
            distance = abs(lap_dist_pct - corner_pos)
            if distance > 0.5:  # Wrap around track
                distance = 1.0 - distance
                
            if distance < min_distance and distance < 0.08:  # Within 8% of track
                min_distance = distance
                closest_corner = corner_name
                
        return closest_corner
    
    def process_telemetry(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Process incoming telemetry and generate coaching messages"""
        try:
            # Add to telemetry buffer
            telemetry['timestamp'] = time.time()
            self.telemetry_buffer.append(telemetry.copy())
            
            # Update current lap data
            self._update_current_lap_data(telemetry)
            
            # Track position analysis for corner-specific coaching
            self._analyze_track_position(telemetry)
            
            # Vehicle dynamics analysis for oversteer/understeer detection
            self._analyze_vehicle_dynamics(telemetry)
            
            # Generate coaching messages
            messages = []
            
            # If baseline not established, only show countdown message
            if not self.baseline_established:
                countdown_message = self._generate_baseline_countdown(telemetry)
                if countdown_message:
                    messages.append(countdown_message)
                # Return early - no other messages until baseline is established
                return self._prioritize_messages(messages)
            
            # Baseline is established - show all coaching messages
            # Track-specific corner coaching (priority)
            messages.extend(self._generate_corner_specific_coaching(telemetry))
            
            # Vehicle dynamics coaching (oversteer/understeer)
            messages.extend(self._generate_handling_coaching(telemetry))
            
            # Immediate feedback - tire/brake pattern analysis
            messages.extend(self._analyze_tire_management(telemetry))
            messages.extend(self._analyze_brake_usage(telemetry))
            messages.extend(self._analyze_throttle_application(telemetry))
            messages.extend(self._analyze_track_surface(telemetry))  # Track surface analysis
            
            # General coaching tips
            messages.extend(self._generate_general_tips(telemetry))
            
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
                # Note: Tire temps removed - iRacing doesn't provide reliable data during racing
            },
            'brake_temps': {
                # Note: Brake temps removed - iRacing doesn't provide reliable data during racing
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
                self.baseline_just_established = True  # Flag for congratulatory message
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
            # Note: Tire and brake temperature learning removed since iRacing doesn't provide
            # reliable tire/brake temperature data during racing through iRSDK
            
            # 1. Update driving style classification
            self._classify_driving_style(lap)
            
            # 2. Learn track-specific patterns (if we have position data)
            self._learn_track_patterns(lap)
            
            # 3. Adaptive threshold updates
            self._update_adaptive_thresholds(lap)
            
            logger.debug(f"🧠 AI models updated with lap {lap.lap_number} data")
            
        except Exception as e:
            logger.error(f"Error updating AI models: {e}")
    
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
        """Learn track-specific patterns from completed lap data"""
        # Enhanced track learning with corner-specific data
        if hasattr(self, 'track_learning'):
            if 'lap_times' not in self.track_learning:
                self.track_learning['lap_times'] = []
            self.track_learning['lap_times'].append(lap.lap_time)
        else:
            self.track_learning = {'lap_times': [lap.lap_time]}
            
        # Keep only recent data (last 20 laps)
        if len(self.track_learning['lap_times']) > 20:
            self.track_learning['lap_times'] = self.track_learning['lap_times'][-20:]
        
        # Analyze corner performance if we have corner data
        for corner_name, corner_data in self.corner_analysis.items():
            if corner_data['brake_points'] and corner_data['consistent_times']:
                # Find best performing approach for this corner
                if len(corner_data['brake_points']) >= 3:
                    # Find the brake point that correlates with best lap times
                    best_brake_point = self._find_optimal_brake_point(corner_name, corner_data)
                    corner_data['best_brake_point'] = best_brake_point
                    
                if len(corner_data['entry_speeds']) >= 3:
                    # Find optimal entry speed
                    best_entry_speed = self._find_optimal_entry_speed(corner_name, corner_data)
                    corner_data['best_entry_speed'] = best_entry_speed
    
    def _find_optimal_brake_point(self, corner_name: str, corner_data: Dict) -> Optional[float]:
        """Find the optimal brake point for a corner based on performance correlation"""
        if len(corner_data['brake_points']) < 3 or len(corner_data['consistent_times']) < 3:
            return None
            
        # Simple correlation: find brake point used during best laps
        # More sophisticated analysis could use statistical correlation
        if len(self.laps) >= 3:
            recent_laps = self.laps[-5:]  # Last 5 laps
            best_lap_times = sorted([lap.lap_time for lap in recent_laps if lap.lap_time > 0])[:2]  # Top 2
            
            if best_lap_times:
                avg_best_time = np.mean(best_lap_times)
                # Find brake points from laps close to best times
                optimal_brake_points = []
                for i, brake_point in enumerate(corner_data['brake_points'][-5:]):  # Recent brake points
                    if i < len(corner_data['consistent_times']) and corner_data['consistent_times'][i] <= avg_best_time * 1.02:
                        optimal_brake_points.append(brake_point)
                
                if optimal_brake_points:
                    return np.mean(optimal_brake_points)
        
        return None
    
    def _find_optimal_entry_speed(self, corner_name: str, corner_data: Dict) -> Optional[float]:
        """Find the optimal entry speed for a corner"""
        if len(corner_data['entry_speeds']) < 3:
            return None
            
        # Similar logic to brake points - find speeds during best laps
        if len(self.laps) >= 3:
            recent_laps = self.laps[-5:]
            best_lap_times = sorted([lap.lap_time for lap in recent_laps if lap.lap_time > 0])[:2]
            
            if best_lap_times:
                avg_best_time = np.mean(best_lap_times)
                optimal_speeds = []
                for i, entry_speed in enumerate(corner_data['entry_speeds'][-5:]):
                    if i < len(corner_data['consistent_times']) and corner_data['consistent_times'][i] <= avg_best_time * 1.02:
                        optimal_speeds.append(entry_speed)
                
                if optimal_speeds:
                    return np.mean(optimal_speeds)
        
        return None
    
    def _analyze_track_position(self, telemetry: Dict[str, Any]):
        """Analyze current track position and update corner-specific data"""
        lap_dist_pct = telemetry.get('lapDistPct', 0)
        speed = telemetry.get('speed', 0)
        brake = telemetry.get('brake', 0)
        throttle = telemetry.get('throttle', 0)
        current_lap_time = telemetry.get('lapCurrentLapTime', 0)
        
        # Identify current corner
        corner = self._identify_corner_from_position(lap_dist_pct)
        
        if corner and corner != self.current_corner:
            # Entering new corner
            self.current_corner = corner
            self.in_braking_zone = False
        
        # Track braking events for corner analysis
        if corner and brake > 30:  # Significant braking
            if not self.in_braking_zone:
                # Start of braking zone
                self.in_braking_zone = True
                self.corner_analysis[corner]['brake_points'].append(lap_dist_pct)
                self.corner_analysis[corner]['entry_speeds'].append(speed)
                
                # Keep only recent data (last 10 brake points per corner)
                if len(self.corner_analysis[corner]['brake_points']) > 10:
                    self.corner_analysis[corner]['brake_points'] = self.corner_analysis[corner]['brake_points'][-10:]
                    self.corner_analysis[corner]['entry_speeds'] = self.corner_analysis[corner]['entry_speeds'][-10:]
        
        elif corner and brake < 10 and self.in_braking_zone:
            # End of braking zone
            self.in_braking_zone = False
            if speed > 0:
                self.corner_analysis[corner]['exit_speeds'].append(speed)
                self.corner_analysis[corner]['consistent_times'].append(current_lap_time)
                
                # Keep only recent data
                if len(self.corner_analysis[corner]['exit_speeds']) > 10:
                    self.corner_analysis[corner]['exit_speeds'] = self.corner_analysis[corner]['exit_speeds'][-10:]
                    self.corner_analysis[corner]['consistent_times'] = self.corner_analysis[corner]['consistent_times'][-10:]
    
    def _generate_corner_specific_coaching(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Generate specific coaching advice for corners based on learned patterns"""
        messages = []
        
        if not self.current_corner or len(self.laps) < 3:
            return messages
            
        corner_name = self.current_corner
        corner_data = self.corner_analysis[corner_name]
        
        lap_dist_pct = telemetry.get('lapDistPct', 0)
        speed = telemetry.get('speed', 0)
        brake = telemetry.get('brake', 0)
        current_lap_time = telemetry.get('lapCurrentLapTime', 0)
        
        # Only provide advice when we have enough data
        if len(corner_data['brake_points']) < 3:
            return messages
        
        # Check if we're approaching a corner we have data for
        approaching_corner = None
        for corner_pos, corner_name_check in self.corner_names.items():
            # Check if we're approaching this corner (within 5% track distance before it)
            distance_to_corner = corner_pos - lap_dist_pct
            if distance_to_corner < 0:
                distance_to_corner += 1.0  # Handle track wrap
            
            if 0.02 < distance_to_corner < 0.05:  # 2-5% before corner
                approaching_corner = corner_name_check
                break
        
        if approaching_corner and approaching_corner in self.corner_analysis:
            approach_data = self.corner_analysis[approaching_corner]
            
            # Brake point coaching
            if approach_data['best_brake_point'] and len(approach_data['brake_points']) >= 3:
                current_brake_tendency = np.mean(approach_data['brake_points'][-3:])  # Recent tendency
                optimal_brake_point = approach_data['best_brake_point']
                
                difference = current_brake_tendency - optimal_brake_point
                
                if abs(difference) > 0.015:  # More than 1.5% track distance difference
                    if difference > 0:  # Braking too late
                        messages.append(CoachingMessage(
                            message=f"Try braking earlier into {approaching_corner} - about {difference*100:.1f}% sooner",
                            category="corner_specific",
                            priority=9,
                            confidence=85,
                            data_source=f"corner_analysis_{approaching_corner}",
                            improvement_potential=0.1
                        ))
                    else:  # Braking too early
                        messages.append(CoachingMessage(
                            message=f"You can brake later into {approaching_corner} - try {abs(difference)*100:.1f}% later",
                            category="corner_specific", 
                            priority=9,
                            confidence=85,
                            data_source=f"corner_analysis_{approaching_corner}",
                            improvement_potential=0.08
                        ))
            
            # Entry speed coaching
            if approach_data['best_entry_speed'] and len(approach_data['entry_speeds']) >= 3:
                current_entry_tendency = np.mean(approach_data['entry_speeds'][-3:])
                optimal_entry_speed = approach_data['best_entry_speed']
                
                speed_difference = current_entry_tendency - optimal_entry_speed
                
                if abs(speed_difference) > 5:  # More than 5 mph/kph difference
                    if speed_difference < -5:  # Too slow
                        messages.append(CoachingMessage(
                            message=f"Carry more speed into {approaching_corner} - try {abs(speed_difference):.0f} faster entry",
                            category="corner_specific",
                            priority=8,
                            confidence=80,
                            data_source=f"corner_speed_{approaching_corner}",
                            improvement_potential=0.12
                        ))
                    elif speed_difference > 5:  # Too fast
                        messages.append(CoachingMessage(
                            message=f"Entry speed too high for {approaching_corner} - try {speed_difference:.0f} slower",
                            category="corner_specific",
                            priority=8,
                            confidence=80,
                            data_source=f"corner_speed_{approaching_corner}",
                            improvement_potential=0.15
                        ))
        
        # Current corner performance feedback
        if brake > 30 and corner_data['brake_points']:  # Currently braking in analyzed corner
            recent_brake_points = corner_data['brake_points'][-5:]  # Last 5 times through this corner
            current_position = lap_dist_pct
            
            # Check consistency
            if len(recent_brake_points) >= 3:
                brake_consistency = np.std(recent_brake_points) / np.mean(recent_brake_points)
                if brake_consistency > 0.05:  # Inconsistent braking
                    messages.append(CoachingMessage(
                        message=f"Brake point consistency in {corner_name} needs work - focus on same reference point",
                        category="corner_specific",
                        priority=6,
                        confidence=75,
                        data_source=f"corner_consistency_{corner_name}",
                        improvement_potential=0.08
                    ))
        
        return messages
    
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
    
    def _generate_baseline_countdown(self, telemetry: Dict[str, Any]) -> Optional[CoachingMessage]:
        """Generate countdown message showing laps remaining until baseline is established"""
        # Only show during active driving (not while stationary)
        speed = telemetry.get('speed', 0)
        if speed < 10:  # Only show when actually driving
            return None
        
        # Show congratulatory message when baseline was just established
        if self.baseline_just_established:
            self.baseline_just_established = False  # Reset flag after showing message
            return CoachingMessage(
                message="🎉 AI Baseline established! Advanced coaching now active - I'm learning your driving style!",
                category="baseline",
                priority=8,  # High priority for congratulatory message
                confidence=100.0,
                data_source="baseline_completion"
            )
        
        # Show countdown if baseline not yet established
        if not self.baseline_established:
            completed_laps = len(self.laps)
            laps_needed = 3
            laps_remaining = max(0, laps_needed - completed_laps)
            
            if laps_remaining > 0:
                if completed_laps == 0:
                    message = f"🏁 Complete {laps_remaining} laps to establish AI baseline for advanced coaching"
                elif laps_remaining == 1:
                    message = f"🏁 Just {laps_remaining} more lap needed for AI baseline! Keep driving..."
                else:
                    message = f"🏁 {laps_remaining} more laps needed for AI baseline ({completed_laps}/{laps_needed} completed)"
                
                return CoachingMessage(
                    message=message,
                    category="baseline",
                    priority=3,  # Medium priority - informative but not urgent
                    confidence=100.0,
                    data_source="lap_tracking"
                )
        
        return None
    
    def _generate_general_tips(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Generate general coaching tips that don't require specific driving data"""
        messages = []
        current_time = time.time()
        speed = telemetry.get('speed', 0)
        
        # Generate different tips based on driving state and time
        tip_sets = {
            'preparation': [
                "Focus on smooth inputs - consistency beats speed",
                "Remember: brake in a straight line for maximum efficiency",
                "Trail braking helps rotate the car through corners",
                "Look ahead - where you look is where you'll go",
                "Exit speed matters more than entry speed"
            ],
            'technical': [
                "ABS activated? You're braking too hard - ease off slightly",
                "Traction control kicking in? Progressive throttle is key",
                "Weight transfer is your friend - use it wisely",
                "Find the racing line and stick to it",
                "Smooth inputs lead to faster lap times"
            ],
            'mental': [
                "Stay calm and focused - panic leads to mistakes",
                "Every corner is a learning opportunity",
                "Patience wins races - don't overdrive the car",
                "Small improvements compound over time",
                "Trust the process - speed will come naturally"
            ],
            'racecraft': [
                "Defend the inside line but leave racing room",
                "Plan your overtakes - patience creates opportunities",
                "Watch your mirrors but don't let them distract you",
                "Position matters - think three corners ahead",
                "Racing is chess at 150mph - think strategically"
            ]
        }
        
        # Select a category based on session time to provide variety
        categories = list(tip_sets.keys())
        category_index = int((current_time / 10) % len(categories))  # Change every 10 seconds
        selected_category = categories[category_index]
        
        # Select a tip from the category that hasn't been used recently
        available_tips = []
        for tip in tip_sets[selected_category]:
            if tip not in self.recent_messages or \
               current_time - self.recent_messages[tip] > self.message_cooldown:
                available_tips.append(tip)
        
        if available_tips and len(messages) < 2:  # Only add if we don't have many messages
            import random
            selected_tip = random.choice(available_tips)
            messages.append(CoachingMessage(
                message=selected_tip,
                category=f"tip_{selected_category}",
                priority=3,
                confidence=85,
                data_source="general_tips"
            ))
        
        return messages
    
    def _analyze_tire_management(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze tire usage patterns based on driving behavior (no temperature data)"""
        messages = []
        
        # Note: Tire temperature analysis removed since iRacing doesn't provide reliable
        # tire temperature data during racing through iRSDK. 
        # This function is kept for future tire pressure/wear analysis if data becomes available.
        
        speed = telemetry.get('speed', 0)
        throttle = telemetry.get('throttle', 0)
        brake = telemetry.get('brake', 0)
        
        # Analyze tire usage patterns based on driving behavior
        if len(self.telemetry_buffer) >= 10:
            # Check for aggressive driving that could harm tires
            recent_data = list(self.telemetry_buffer)[-10:]
            
            # Count hard braking events
            hard_braking_count = sum(1 for data in recent_data if data.get('brake', 0) > 90)
            
            # Count aggressive throttle applications
            aggressive_throttle_count = 0
            for i in range(1, len(recent_data)):
                throttle_delta = recent_data[i].get('throttle', 0) - recent_data[i-1].get('throttle', 0)
                if throttle_delta > 40:  # Sudden throttle spike
                    aggressive_throttle_count += 1
            
            if hard_braking_count >= 3:
                messages.append(CoachingMessage(
                    message="Frequent hard braking detected - try smoother inputs for better tire life",
                    category="tires",
                    priority=5,
                    confidence=70,
                    data_source="driving_pattern"
                ))
            
            if aggressive_throttle_count >= 3:
                messages.append(CoachingMessage(
                    message="Aggressive throttle inputs detected - smooth application preserves tires",
                    category="tires", 
                    priority=4,
                    confidence=70,
                    data_source="driving_pattern"
                ))
        
        return messages
    
    def _analyze_brake_usage(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze braking patterns and technique (no temperature data)"""
        messages = []
        
        brake_pressure = telemetry.get('brake', 0)
        speed = telemetry.get('speed', 0)
        
        # Note: Brake temperature analysis removed since iRacing doesn't provide reliable
        # brake temperature data during racing through iRSDK.
        # Focus on braking technique and pressure patterns instead.
        
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
        
        # Check for brake/throttle overlap (trail braking analysis)
        throttle = telemetry.get('throttle', 0)
        if brake_pressure > 20 and throttle > 20:
            # Could be trail braking (good) or poor technique (bad)
            if speed > 80:  # High speed = likely good trail braking
                if not hasattr(self, '_last_trail_brake_tip') or time.time() - self._last_trail_brake_tip > 15:
                    messages.append(CoachingMessage(
                        message="Good trail braking technique - helps rotate the car",
                        category="braking",
                        priority=2,
                        confidence=60,
                        data_source="trail_braking"
                    ))
                    self._last_trail_brake_tip = time.time()
            else:  # Low speed = likely poor technique
                messages.append(CoachingMessage(
                    message="Avoid brake/throttle overlap at low speeds - choose one input",
                    category="braking",
                    priority=6,
                    confidence=75,
                    data_source="input_overlap"
                ))
        
        # Analyze braking consistency over time
        if len(self.telemetry_buffer) >= 20:
            recent_brake_events = []
            for data in list(self.telemetry_buffer)[-20:]:
                if data.get('brake', 0) > 50:  # Significant braking
                    recent_brake_events.append(data.get('brake', 0))
            
            if len(recent_brake_events) >= 5:
                brake_variance = np.std(recent_brake_events) / np.mean(recent_brake_events)
                if brake_variance > 0.3:  # High variance in brake pressure
                    if not hasattr(self, '_last_brake_consistency_tip') or time.time() - self._last_brake_consistency_tip > 20:
                        messages.append(CoachingMessage(
                            message="Brake pressure consistency could improve - practice smooth inputs",
                            category="braking",
                            priority=3,
                            confidence=65,
                            data_source="brake_consistency"
                        ))
                        self._last_brake_consistency_tip = time.time()
        
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
        """Analyze racing line efficiency with track position awareness"""
        messages = []
        
        speed = telemetry.get('speed', 0)
        throttle = telemetry.get('throttle', 0)
        brake = telemetry.get('brake', 0)
        lap_dist_pct = telemetry.get('lapDistPct', 0)
        
        # Track position specific racing line analysis
        if self.current_corner:
            corner_data = self.corner_analysis[self.current_corner]
            
            # Analyze racing line based on speed traces through corners
            if len(corner_data['exit_speeds']) >= 3:
                recent_exit_speeds = corner_data['exit_speeds'][-3:]
                avg_exit_speed = np.mean(recent_exit_speeds)
                
                # Compare to best exits
                if corner_data['exit_speeds']:
                    best_exits = sorted(corner_data['exit_speeds'], reverse=True)[:2]
                    if best_exits:
                        target_exit_speed = np.mean(best_exits)
                        
                        if avg_exit_speed < target_exit_speed * 0.95:  # 5% slower than best
                            messages.append(CoachingMessage(
                                message=f"Focus on exit speed from {self.current_corner} - you've done {target_exit_speed:.0f} before",
                                category="racing_line",
                                priority=7,
                                confidence=80,
                                data_source=f"exit_speed_{self.current_corner}",
                                improvement_potential=0.1
                            ))
        
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
    
    def _analyze_track_surface(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Analyze track surface and provide feedback about track position"""
        messages = []
        
        track_surface = telemetry.get('playerTrackSurface', 4)  # Default to on_track
        speed = telemetry.get('speed', 0)
        throttle = telemetry.get('throttle', 0)
        brake = telemetry.get('brake', 0)
        
        # Track surface mapping
        surface_names = {
            0: "not_in_world",
            1: "off_track", 
            2: "in_pit_stall",
            3: "approaching_pits", 
            4: "on_track"
        }
        
        surface_name = surface_names.get(track_surface, "unknown")
        
        # Analysis for off-track situations
        if track_surface == 1 and speed > 10:  # Off track at decent speed
            # Determine likely cause based on inputs
            if brake > 30:
                messages.append(CoachingMessage(
                    message="Went off track under braking - try braking earlier and smoother",
                    category="braking",
                    priority=8,
                    confidence=85,
                    data_source="track_surface_braking",
                    improvement_potential=0.2
                ))
            elif throttle > 50:
                messages.append(CoachingMessage(
                    message="Went off track on throttle - ease into the power to maintain grip",
                    category="throttle", 
                    priority=8,
                    confidence=85,
                    data_source="track_surface_throttle",
                    improvement_potential=0.15
                ))
            else:
                # General cornering advice
                messages.append(CoachingMessage(
                    message="Went off track in corner - focus on smooth inputs and racing line",
                    category="racing_line",
                    priority=7,
                    confidence=80,
                    data_source="track_surface_cornering",
                    improvement_potential=0.1
                ))
        
        # Check recent track surface history for pattern analysis
        if len(self.telemetry_buffer) >= 30:  # Have half second of data
            recent_surfaces = [t.get('playerTrackSurface', 4) for t in list(self.telemetry_buffer)[-30:]]
            off_track_count = sum(1 for surface in recent_surfaces if surface == 1)
            
            # If more than 20% of recent samples are off-track, suggest consistency work
            if off_track_count > 6:  # More than 20% off track in last 30 samples
                messages.append(CoachingMessage(
                    message="Multiple track limit violations - focus on consistency over speed",
                    category="racing_line",
                    priority=6,
                    confidence=75,
                    data_source="track_surface_pattern",
                    improvement_potential=0.3
                ))
        
        # Positive reinforcement for good track position
        if track_surface == 4 and speed > 30:  # On track at good speed
            # Only occasionally give positive feedback to avoid spam
            if len(self.telemetry_buffer) > 0 and len(self.telemetry_buffer) % 300 == 0:  # Every 5 seconds
                recent_on_track = [t.get('playerTrackSurface', 4) for t in list(self.telemetry_buffer)[-180:]]  # Last 3 seconds
                if all(surface == 4 for surface in recent_on_track):
                    messages.append(CoachingMessage(
                        message="Good car control - staying on the racing line consistently",
                        category="racing_line",
                        priority=3,
                        confidence=70,
                        data_source="track_surface_positive"
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
            # Provide varied default messages to prevent monotony
            default_messages = [
                "All systems looking good - keep it up!",
                "Ready to race - systems are green!",
                "Car setup looks optimal - let's go racing!",
                "Telemetry nominal - ready for action!",
                "Everything checks out - time to hit the track!",
                "All systems go - show them what you've got!",
                "Perfect conditions - make every lap count!"
            ]
            
            # Select a message that hasn't been used recently
            import random
            available_messages = []
            for msg in default_messages:
                if msg not in self.recent_messages or \
                   current_time - self.recent_messages[msg] > self.message_cooldown:
                    available_messages.append(msg)
            
            if available_messages:
                selected_msg = random.choice(available_messages)
                self.recent_messages[selected_msg] = current_time
                return [CoachingMessage(
                    message=selected_msg,
                    category="general",
                    priority=2,
                    confidence=80,
                    data_source="default"
                )]
            else:
                return []  # Return empty if all messages are on cooldown
        
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
            "coaching_intensity": getattr(self, 'coaching_intensity', 1.0)
            # Note: tire/brake temp learning removed - iRacing doesn't provide reliable data
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
    
    def _analyze_vehicle_dynamics(self, telemetry: Dict[str, Any]):
        """Analyze vehicle dynamics for oversteer/understeer detection"""
        try:
            # Extract vehicle dynamics data
            steering_angle = telemetry.get('steering', 0)  # SteeringWheelAngle in radians
            yaw_rate = telemetry.get('yawRate', 0)         # YawRate in rad/s
            lat_accel = telemetry.get('latAccel', 0)       # Lateral acceleration in G
            long_accel = telemetry.get('longAccel', 0)     # Longitudinal acceleration in G
            velocity_x = telemetry.get('velocityX', 0)     # Forward velocity
            velocity_y = telemetry.get('velocityY', 0)     # Lateral velocity (slip)
            speed = telemetry.get('speed', 0)              # Total speed
            throttle = telemetry.get('throttle', 0)        # Throttle position
            brake = telemetry.get('brake', 0)              # Brake position
            
            # Only analyze when car is moving meaningfully
            if speed < 15:  # Below ~15 mph/kph, dynamics analysis not meaningful
                return
                
            # Calculate slip angle approximation using velocity components
            # Slip angle ≈ arctan(lateral_velocity / forward_velocity)
            if abs(velocity_x) > 0.1:  # Avoid division by zero
                estimated_slip_angle = abs(velocity_y / velocity_x)
            else:
                estimated_slip_angle = 0
                
            # Store dynamics data in history buffer
            dynamics_data = {
                'timestamp': time.time(),
                'steering_angle': steering_angle,
                'yaw_rate': yaw_rate, 
                'lat_accel': lat_accel,
                'long_accel': long_accel,
                'slip_angle': estimated_slip_angle,
                'speed': speed,
                'throttle': throttle,
                'brake': brake,
                'corner': self.current_corner
            }
            
            self.steering_response_history.append(dynamics_data)
            
            # Analyze for oversteer/understeer patterns
            self._detect_handling_characteristics(dynamics_data)
            
        except Exception as e:
            logger.error(f"Error in vehicle dynamics analysis: {e}")
    
    def _detect_handling_characteristics(self, dynamics_data: Dict[str, Any]):
        """Detect oversteer and understeer based on vehicle dynamics"""
        try:
            # Need sufficient history for analysis  
            if len(self.steering_response_history) < 20:  # Need ~0.3 seconds of data
                return
                
            current_time = dynamics_data['timestamp']
            steering_angle = abs(dynamics_data['steering_angle'])
            yaw_rate = abs(dynamics_data['yaw_rate'])
            lat_accel = abs(dynamics_data['lat_accel'])
            slip_angle = dynamics_data['slip_angle']
            speed = dynamics_data['speed']
            corner = dynamics_data['corner']
            
            # Only analyze in corners with meaningful steering input
            if steering_angle < 0.1 or speed < 20:  # Minimal steering or too slow
                return
                
            # Get recent history for trend analysis
            recent_data = [d for d in self.steering_response_history 
                          if current_time - d['timestamp'] < 2.0]  # Last 2 seconds
            
            if len(recent_data) < 10:
                return
                
            # Calculate expected vs actual yaw response
            # In ideal conditions: yaw_rate should be proportional to steering_angle * speed
            # Deviations indicate oversteer (too much yaw) or understeer (too little yaw)
            
            # Expected yaw rate calculation (simplified)
            # This is a basic approximation - real cars have complex dynamics
            expected_yaw_rate = steering_angle * (speed / 100.0) * 0.5  # Scaling factor
            
            yaw_response_ratio = yaw_rate / max(expected_yaw_rate, 0.001)  # Avoid division by zero
            
            # Lateral acceleration should correlate with yaw rate and speed
            expected_lat_accel = (yaw_rate * speed) / 9.81  # Convert to G-force approximation
            lat_accel_ratio = lat_accel / max(expected_lat_accel, 0.001)
            
            # Analyze trends over recent data
            recent_yaw_ratios = []
            recent_lat_ratios = []
            
            for data in recent_data[-10:]:  # Last 10 samples
                if data['steering_angle'] > 0.05 and data['speed'] > 15:
                    exp_yaw = data['steering_angle'] * (data['speed'] / 100.0) * 0.5
                    exp_lat = (data['yaw_rate'] * data['speed']) / 9.81;
                    
                    if exp_yaw > 0.001:
                        recent_yaw_ratios.append(data['yaw_rate'] / exp_yaw)
                    if exp_lat > 0.001:
                        recent_lat_ratios.append(data['lat_accel'] / exp_lat)
            
            if len(recent_yaw_ratios) < 5:
                return
                
            avg_yaw_ratio = np.mean(recent_yaw_ratios)
            avg_lat_ratio = np.mean(recent_lat_ratios) if recent_lat_ratios else 1.0;
            
            # Detection thresholds
            oversteer_threshold = 1.3   # Yaw rate > 30% higher than expected
            understeer_threshold = 0.7  # Yaw rate < 30% of expected
            
            # Detect oversteer: too much yaw response for steering input
            if avg_yaw_ratio > oversteer_threshold and slip_angle > 0.1:
                self._record_oversteer_event(corner, dynamics_data, avg_yaw_ratio)
                
            # Detect understeer: insufficient yaw response for steering input  
            elif avg_yaw_ratio < understeer_threshold and steering_angle > 0.2:
                self._record_understeer_event(corner, dynamics_data, avg_yaw_ratio)
                
        except Exception as e:
            logger.error(f"Error detecting handling characteristics: {e}")
    
    def _record_oversteer_event(self, corner: str, dynamics_data: Dict[str, Any], yaw_ratio: float):
        """Record an oversteer event for analysis and coaching"""
        current_time = time.time()
        
        # Avoid spam - only record if it's been a while since last oversteer message
        if hasattr(self, '_last_oversteer_message') and current_time - self._last_oversteer_message < 5.0:
            return
            
        event = {
            'timestamp': current_time,
            'corner': corner,
            'yaw_ratio': yaw_ratio,
            'speed': dynamics_data['speed'],
            'throttle': dynamics_data['throttle'],
            'brake': dynamics_data['brake'],
            'steering_angle': dynamics_data['steering_angle']
        }
        
        if corner:
            self.oversteer_events[corner].append(event)
            # Keep only recent events (last 10 per corner)
            if len(self.oversteer_events[corner]) > 10:
                self.oversteer_events[corner] = self.oversteer_events[corner][-10:]
        
        self._last_oversteer_message = current_time
        logger.info(f"🌀 Oversteer detected in {corner or 'unknown corner'} - yaw ratio: {yaw_ratio:.2f}")
    
    def _record_understeer_event(self, corner: str, dynamics_data: Dict[str, Any], yaw_ratio: float):
        """Record an understeer event for analysis and coaching"""
        current_time = time.time()
        
        # Avoid spam - only record if it's been a while since last understeer message
        if hasattr(self, '_last_understeer_message') and current_time - self._last_understeer_message < 5.0:
            return
            
        event = {
            'timestamp': current_time,
            'corner': corner,
            'yaw_ratio': yaw_ratio,
            'speed': dynamics_data['speed'],
            'throttle': dynamics_data['throttle'],
            'brake': dynamics_data['brake'],
            'steering_angle': dynamics_data['steering_angle']
        }
        
        if corner:
            self.understeer_events[corner].append(event)
            # Keep only recent events (last 10 per corner)
            if len(self.understeer_events[corner]) > 10:
                self.understeer_events[corner] = self.understeer_events[corner][-10:]
        
        self._last_understeer_message = current_time
        logger.info(f"🔄 Understeer detected in {corner or 'unknown corner'} - yaw ratio: {yaw_ratio:.2f}")
    
    def _generate_handling_coaching(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Generate coaching messages based on handling analysis"""
        messages = []
        
        if not self.baseline_established or len(self.laps) < 2:
            return messages
            
        current_time = time.time()
        corner = self.current_corner
        
        # Oversteer coaching
        if corner and corner in self.oversteer_events:
            recent_oversteer = [e for e in self.oversteer_events[corner] 
                              if current_time - e['timestamp'] < 30.0]  # Last 30 seconds
            
            if len(recent_oversteer) >= 2:  # Multiple oversteer events recently
                # Analyze pattern
                on_throttle_oversteer = sum(1 for e in recent_oversteer if e['throttle'] > 30)
                on_brake_oversteer = sum(1 for e in recent_oversteer if e['brake'] > 30)
                
                if on_throttle_oversteer >= len(recent_oversteer) * 0.7:  # Mostly on throttle
                    messages.append(CoachingMessage(
                        message=f"Oversteer on throttle in {corner} - ease into the power more gradually",
                        category="handling",
                        priority=8,
                        confidence=85,
                        data_source=f"oversteer_analysis_{corner}",
                        improvement_potential=0.15
                    ))
                elif on_brake_oversteer >= len(recent_oversteer) * 0.7:  # Mostly on brakes
                    messages.append(CoachingMessage(
                        message=f"Oversteer under braking in {corner} - try trail braking or brake earlier",
                        category="handling",
                        priority=8,
                        confidence=85,
                        data_source=f"oversteer_analysis_{corner}",
                        improvement_potential=0.12
                    ))
                else:  # Mixed or entry oversteer
                    messages.append(CoachingMessage(
                        message=f"Frequent oversteer in {corner} - reduce entry speed or smoother inputs",
                        category="handling",
                        priority=7,
                        confidence=80,
                        data_source=f"oversteer_analysis_{corner}",
                        improvement_potential=0.1
                    ))
        
        # Understeer coaching
        if corner and corner in self.understeer_events:
            recent_understeer = [e for e in self.understeer_events[corner] 
                               if current_time - e['timestamp'] < 30.0]  # Last 30 seconds
            
            if len(recent_understeer) >= 2:  # Multiple understeer events recently
                # Analyze pattern
                high_speed_understeer = sum(1 for e in recent_understeer if e['speed'] > 60)
                on_throttle_understeer = sum(1 for e in recent_understeer if e['throttle'] > 50)
                
                if high_speed_understeer >= len(recent_understeer) * 0.7:  # High speed understeer
                    messages.append(CoachingMessage(
                        message=f"High-speed understeer in {corner} - reduce entry speed or trail brake",
                        category="handling",
                        priority=8,
                        confidence=85,
                        data_source=f"understeer_analysis_{corner}",
                        improvement_potential=0.2
                    ))
                elif on_throttle_understeer >= len(recent_understeer) * 0.7:  # Throttle understeer
                    messages.append(CoachingMessage(
                        message=f"Power understeer in {corner} - wait for car rotation before throttle",
                        category="handling",
                        priority=7,
                        confidence=80,
                        data_source=f"understeer_analysis_{corner}",
                        improvement_potential=0.12
                    ))
                else:  # General understeer
                    messages.append(CoachingMessage(
                        message=f"Frequent understeer in {corner} - try later braking or different line",
                        category="handling",
                        priority=6,
                        confidence=75,
                        data_source=f"understeer_analysis_{corner}",
                        improvement_potential=0.08
                    ))
        
        return messages
