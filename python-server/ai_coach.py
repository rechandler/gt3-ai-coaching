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
                # Return early - no other messages until baseline is established
                return self._prioritize_messages(messages)
            
            # Baseline is established - show all coaching messages
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
