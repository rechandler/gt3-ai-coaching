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
import threading
import queue
import random

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

@dataclass
class VehicleDynamicsState:
    """Real-time vehicle dynamics analysis"""
    timestamp: float
    speed: float
    gear: int
    rpm: float
    throttle: float
    brake: float
    steering_angle: float
    lat_accel: float  # Lateral G-force
    long_accel: float  # Longitudinal G-force
    vert_accel: float  # Vertical G-force
    yaw_rate: float
    pitch: float
    roll: float
    weight_distribution_front: float  # Calculated front weight %
    weight_distribution_rear: float   # Calculated rear weight %
    aero_balance: float  # Aerodynamic balance estimation
    track_position: float  # lapDistPct
    corner_radius: Optional[float] = None  # Estimated corner radius
    slip_angle: Optional[float] = None     # Estimated slip angle

@dataclass 
class GearShiftEvent:
    """Gear shifting analysis event"""
    timestamp: float
    from_gear: int
    to_gear: int
    shift_type: str  # 'upshift', 'downshift', 'missed_shift', 'rev_match'
    rpm_at_shift: float
    speed_at_shift: float
    throttle_at_shift: float
    brake_at_shift: float
    shift_duration: float  # Time taken for shift
    rpm_drop: Optional[float] = None  # For upshifts
    rpm_rise: Optional[float] = None  # For downshifts
    engine_braking_utilized: bool = False
    rev_matching_quality: float = 0.0  # 0-100 score
    optimal_shift_point_delta: float = 0.0  # How far from optimal
    track_position: float = 0.0
    corner: Optional[str] = None

@dataclass
class WeightTransferAnalysis:
    """Weight transfer and vehicle balance analysis"""
    timestamp: float
    longitudinal_transfer: float  # Forward/backward weight shift (G)
    lateral_transfer: float       # Left/right weight shift (G)
    front_axle_load: float       # Percentage of weight on front
    rear_axle_load: float        # Percentage of weight on rear
    understeer_gradient: float   # Understeer/oversteer tendency
    grip_utilization: float      # How much of available grip is used (0-1)
    stability_margin: float      # How close to limit (0-1)
    braking_efficiency: float    # How efficiently brakes are used
    traction_efficiency: float   # How efficiently throttle is used

@dataclass 
class GForceAnalysis:
    """G-force and acceleration analysis"""
    timestamp: float
    peak_lat_g: float           # Peak lateral G in this sample
    peak_long_g: float          # Peak longitudinal G in this sample
    peak_combined_g: float      # Peak combined G-force
    g_force_smoothness: float   # How smooth G transitions are (0-1)
    grip_circle_utilization: float  # How much of grip circle is used
    excessive_g_events: int     # Count of excessive G-force spikes
    optimal_g_range: bool       # Whether G-forces are in optimal range

@dataclass
class LLMCoachingContext:
    """Context data for LLM coaching analysis"""
    session_summary: Dict[str, Any]
    recent_telemetry: List[Dict[str, Any]]
    recent_messages: List[str]
    driver_style: str
    coaching_intensity: float
    current_issues: List[str]
    improvements_made: List[str]

@dataclass
class LLMResponse:
    """Response from LLM coaching system"""
    enhanced_message: str
    explanation: str
    session_advice: Optional[str] = None
    confidence: float = 0.0
    
class LocalLLMClient:
    """Simple client for local LLM integration (Ollama, LM Studio, etc.)"""
    
    def __init__(self, enabled: bool = False, model: str = "llama3.1:8b"):
        self.enabled = enabled
        self.model = model
        self.base_url = "http://localhost:11434"  # Ollama default
        
    def enhance_coaching_message(self, message: str, context: LLMCoachingContext) -> LLMResponse:
        """Enhance a coaching message with natural language explanation"""
        if not self.enabled:
            return LLMResponse(
                enhanced_message=message,
                explanation="",
                confidence=0.0
            )
        
        try:
            prompt = self._build_enhancement_prompt(message, context)
            response = self._call_llm(prompt)
            return self._parse_enhancement_response(response, message)
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            return LLMResponse(
                enhanced_message=message,
                explanation="",
                confidence=0.0
            )
    
    def generate_session_analysis(self, context: LLMCoachingContext) -> str:
        """Generate comprehensive session analysis"""
        if not self.enabled:
            return "Session analysis requires LLM integration"
            
        try:
            prompt = self._build_session_prompt(context)
            return self._call_llm(prompt)
        except Exception as e:
            logger.warning(f"Session analysis failed: {e}")
            return "Session analysis temporarily unavailable"
    
    def _build_enhancement_prompt(self, message: str, context: LLMCoachingContext) -> str:
        """Build prompt for message enhancement"""
        style_map = {
            "consistent": "supportive and encouraging",
            "developing": "detailed and instructional", 
            "improving": "motivational and technical"
        }
        
        communication_style = style_map.get(context.driver_style, "balanced")
        
        return f"""
You are an expert GT3 racing coach. Enhance this coaching message with a natural explanation.

Original message: "{message}"

Driver context:
- Style: {context.driver_style}
- Communication preference: {communication_style}
- Recent performance: {len(context.recent_telemetry)} telemetry samples
- Current issues: {', '.join(context.current_issues) if context.current_issues else 'None'}

Provide:
1. Enhanced message (conversational, {communication_style})
2. Brief explanation of WHY this advice helps
3. Keep it under 150 words total

Format: Enhanced message | Explanation
"""

    def _build_session_prompt(self, context: LLMCoachingContext) -> str:
        """Build prompt for session analysis"""
        return f"""
Analyze this GT3 racing session and provide coaching insights:

Session Data:
- Laps completed: {context.session_summary.get('laps_completed', 0)}
- Best lap: {context.session_summary.get('best_lap_time', 'N/A')}
- Consistency: {context.session_summary.get('consistency', 'N/A')}
- Driving style: {context.driver_style}
- Recent improvements: {', '.join(context.improvements_made) if context.improvements_made else 'None'}
- Current challenges: {', '.join(context.current_issues) if context.current_issues else 'None'}

Provide:
1. Top 3 areas for improvement with specific advice
2. What the driver is doing well
3. Recommended practice focus for next session
4. One mental/strategic tip

Keep response under 300 words, be specific and actionable.
"""

    def _call_llm(self, prompt: str) -> str:
        """Make API call to local LLM (placeholder - implement based on your LLM choice)"""
        # This is a placeholder - implement based on your LLM setup:
        # - Ollama: requests to http://localhost:11434/api/generate
        # - LM Studio: requests to http://localhost:1234/v1/chat/completions
        # - llama.cpp: direct Python bindings
        
        # For now, return a template response
        return "Enhanced coaching message | This helps improve your racing line and lap consistency."
    
    def _parse_enhancement_response(self, response: str, original: str) -> LLMResponse:
        """Parse LLM response into structured format"""
        try:
            if "|" in response:
                enhanced, explanation = response.split("|", 1)
                return LLMResponse(
                    enhanced_message=enhanced.strip(),
                    explanation=explanation.strip(),
                    confidence=0.8
                )
            else:
                return LLMResponse(
                    enhanced_message=response[:100] + "..." if len(response) > 100 else response,
                    explanation="",
                    confidence=0.5
                )
        except Exception:
            return LLMResponse(
                enhanced_message=original,
                explanation="",
                confidence=0.0
            )
    
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
        
        # Advanced Vehicle Dynamics Analysis
        self.gear_shift_history = deque(maxlen=100)  # Last 100 gear shifts
        self.weight_transfer_history = deque(maxlen=300)  # 5 seconds at 60Hz
        self.g_force_history = deque(maxlen=300)  # 5 seconds at 60Hz
        self.previous_gear = 0
        self.last_shift_time = 0
        self.shift_in_progress = False
        
        # Gear shift analysis thresholds
        self.optimal_shift_rpm_ranges = {
            # Default ranges - will be learned per car
            1: (6000, 7500),  # Gear 1 to 2 shift range
            2: (6500, 7800),  # Gear 2 to 3 shift range
            3: (6500, 7800),  # Gear 3 to 4 shift range
            4: (6500, 7800),  # Gear 4 to 5 shift range
            5: (6500, 7800),  # Gear 5 to 6 shift range
            6: (6500, 7800),  # Gear 6 to 7 shift range
        }
        
        # G-force and weight transfer thresholds
        self.max_safe_lat_g = 2.5      # Maximum lateral G before warning
        self.max_safe_long_g = 2.0     # Maximum longitudinal G before warning
        self.smooth_g_threshold = 0.5  # G-force change rate for smoothness
        
        # Vehicle dynamics baseline (learned over time)
        self.vehicle_mass_kg = 1200    # Estimated vehicle mass (GT3 typical)
        self.wheelbase_m = 2.7         # Estimated wheelbase
        self.track_width_m = 1.9       # Estimated track width
        self.cg_height_m = 0.4         # Estimated center of gravity height
        
        # Positive Performance Tracking
        self.corner_personal_bests = defaultdict(float)   # Best speed through each corner
        self.last_positive_feedback = 0                   # Timing for positive messages
        self.recent_improvements = deque(maxlen=20)       # Track recent improvements
        
        # LLM Integration for Natural Language Coaching
        self.llm_client = LocalLLMClient(enabled=False)   # Disabled by default
        self.llm_insights_queue = queue.Queue()           # Background LLM analysis
        self.last_llm_analysis = 0                        # Timing for LLM analysis
        self.current_issues = deque(maxlen=10)            # Track current driving issues
        self.communication_style = "balanced"             # Driver's preferred style
        
        logger.info("🤖 Local AI Coach initialized with advanced dynamics analysis - ready to learn your driving style")
    
    def enable_llm_coaching(self, model: str = "llama3.1:8b", base_url: str = "http://localhost:11434"):
        """Enable LLM-powered natural language coaching"""
        self.llm_client.enabled = True
        self.llm_client.model = model
        self.llm_client.base_url = base_url
        logger.info(f"🧠 LLM coaching enabled with model: {model}")
    
    def set_communication_style(self, style: str):
        """Set driver's preferred communication style"""
        valid_styles = ["supportive", "technical", "motivational", "balanced"]
        if style in valid_styles:
            self.communication_style = style
            logger.info(f"💬 Communication style set to: {style}")
        else:
            logger.warning(f"Invalid style '{style}'. Valid options: {valid_styles}")
    
    def _build_llm_context(self) -> LLMCoachingContext:
        """Build context for LLM analysis"""
        recent_telemetry = list(self.telemetry_buffer)[-60:] if self.telemetry_buffer else []
        recent_message_texts = [msg for msg in list(self.recent_messages.keys())[-5:]]
        
        return LLMCoachingContext(
            session_summary=self.get_session_summary(),
            recent_telemetry=recent_telemetry,
            recent_messages=recent_message_texts,
            driver_style=self.driving_style,
            coaching_intensity=self.coaching_intensity,
            current_issues=list(self.current_issues),
            improvements_made=list(self.recent_improvements)
        )
    
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
            
            # Advanced vehicle dynamics analysis
            self._analyze_gear_shifting(telemetry)
            self._analyze_weight_transfer(telemetry)
            self._analyze_g_forces(telemetry)
            
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
            
            # Advanced vehicle dynamics coaching
            messages.extend(self._generate_gear_shift_coaching(telemetry))
            messages.extend(self._generate_weight_transfer_coaching(telemetry))
            messages.extend(self._generate_g_force_coaching(telemetry))
            
            # Positive feedback for good performance
            messages.extend(self._detect_positive_performance(telemetry))
            
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
            prioritized_messages = self._prioritize_messages(messages)
            
            # Track issues and improvements for LLM context
            self._track_driving_issues(prioritized_messages)
            self._track_improvements(prioritized_messages)
            
            # Enhance high-priority messages with LLM if enabled
            if self.llm_client.enabled and prioritized_messages:
                enhanced_messages = self._enhance_messages_with_llm(prioritized_messages)
                return enhanced_messages
            
            return prioritized_messages
            
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
    
    def _analyze_gear_shifting(self, telemetry: Dict[str, Any]):
        """Analyze gear shifting patterns and technique"""
        try:
            current_gear = telemetry.get('gear', 0)
            current_rpm = telemetry.get('rpm', 0)
            current_speed = telemetry.get('speed', 0)
            current_throttle = telemetry.get('throttle', 0)
            current_brake = telemetry.get('brake', 0)
            current_time = time.time()
            track_position = telemetry.get('lapDistPct', 0)
            
            # Detect gear changes
            if hasattr(self, 'previous_gear') and current_gear != self.previous_gear:
                if self.previous_gear > 0 and current_gear > 0:  # Valid gear change
                    
                    shift_type = "upshift" if current_gear > self.previous_gear else "downshift"
                    shift_duration = current_time - self.last_shift_time if hasattr(self, 'last_shift_time') else 0
                    
                    # Calculate RPM changes
                    rpm_drop = None
                    rpm_rise = None
                    
                    if shift_type == "upshift":
                        # For upshifts, we expect RPM to drop
                        if len(self.telemetry_buffer) >= 2:
                            prev_rpm = self.telemetry_buffer[-2].get('rpm', current_rpm)
                            rpm_drop = prev_rpm - current_rpm
                    else:
                        # For downshifts, we expect RPM to rise
                        if len(self.telemetry_buffer) >= 2:
                            prev_rpm = self.telemetry_buffer[-2].get('rpm', current_rpm)
                            rpm_rise = current_rpm - prev_rpm
                    
                    # Analyze rev matching for downshifts
                    rev_matching_quality = 0.0
                    engine_braking_utilized = False
                    
                    if shift_type == "downshift":
                        # Good rev matching means smooth RPM transition
                        if rpm_rise and 500 <= rpm_rise <= 2000:  # Reasonable RPM increase
                            rev_matching_quality = max(0, 100 - abs(rpm_rise - 1000) / 10)
                        
                        # Engine braking is utilized if throttle is released during downshift
                        engine_braking_utilized = current_throttle < 10
                    
                    # Calculate optimal shift point delta
                    optimal_shift_point_delta = 0.0
                    if shift_type == "upshift" and self.previous_gear in self.optimal_shift_rpm_ranges:
                        optimal_min, optimal_max = self.optimal_shift_rpm_ranges[self.previous_gear]
                        if len(self.telemetry_buffer) >= 2:
                            shift_rpm = self.telemetry_buffer[-2].get('rpm', current_rpm)
                            if shift_rpm < optimal_min:
                                optimal_shift_point_delta = optimal_min - shift_rpm  # Shifted too early
                            elif shift_rpm > optimal_max:
                                optimal_shift_point_delta = shift_rpm - optimal_max  # Shifted too late
                    
                    # Create gear shift event
                    shift_event = GearShiftEvent(
                        timestamp=current_time,
                        from_gear=self.previous_gear,
                        to_gear=current_gear,
                        shift_type=shift_type,
                        rpm_at_shift=current_rpm,
                        speed_at_shift=current_speed,
                        throttle_at_shift=current_throttle,
                        brake_at_shift=current_brake,
                        shift_duration=shift_duration,
                        rpm_drop=rpm_drop,
                        rpm_rise=rpm_rise,
                        engine_braking_utilized=engine_braking_utilized,
                        rev_matching_quality=rev_matching_quality,
                        optimal_shift_point_delta=optimal_shift_point_delta,
                        track_position=track_position,
                        corner=self.current_corner
                    )
                    
                    self.gear_shift_history.append(shift_event)
                    logger.debug(f"🔄 Gear shift: {self.previous_gear}→{current_gear} at {current_rpm}RPM")
                
                self.last_shift_time = current_time
            
            # Update optimal shift points based on performance correlation
            self._learn_optimal_shift_points()
            
            self.previous_gear = current_gear
            
        except Exception as e:
            logger.error(f"Error in gear shifting analysis: {e}")
    
    def _learn_optimal_shift_points(self):
        """Learn optimal shift points based on lap time correlation"""
        if len(self.gear_shift_history) < 10 or len(self.laps) < 3:
            return
        
        try:
            # Find best laps for correlation
            if self.best_lap:
                best_lap_time = self.best_lap.lap_time
                recent_laps = [lap for lap in self.laps[-10:] if lap.lap_time > 0]
                
                if recent_laps:
                    # Get shifts from best performing laps (within 102% of best time)
                    good_lap_threshold = best_lap_time * 1.02
                    
                    for gear in range(1, 7):  # Gears 1-6
                        upshifts_from_gear = [
                            shift for shift in self.gear_shift_history
                            if shift.from_gear == gear and shift.shift_type == "upshift"
                        ]
                        
                        if len(upshifts_from_gear) >= 5:
                            # Get shifts from good laps (this is simplified - would need lap correlation)
                            good_shifts = [shift for shift in upshifts_from_gear[-20:]]  # Recent shifts
                            
                            if good_shifts:
                                shift_rpms = []
                                for shift in good_shifts:
                                    # Reconstruct RPM at shift (simplified)
                                    if shift.rpm_drop:
                                        shift_rpm = shift.rpm_at_shift + shift.rpm_drop
                                        shift_rpms.append(shift_rpm)
                                
                                if len(shift_rpms) >= 3:
                                    # Update optimal range based on good shifts
                                    avg_shift_rpm = np.mean(shift_rpms)
                                    std_shift_rpm = np.std(shift_rpms)
                                    
                                    # Update optimal range (with some conservatism)
                                    new_min = max(5000, avg_shift_rpm - std_shift_rpm)
                                    new_max = min(8000, avg_shift_rpm + std_shift_rpm)
                                    
                                    # Blend with existing range
                                    if gear in self.optimal_shift_rpm_ranges:
                                        old_min, old_max = self.optimal_shift_rpm_ranges[gear]
                                        blended_min = (old_min * 0.7) + (new_min * 0.3)
                                        blended_max = (old_max * 0.7) + (new_max * 0.3)
                                        self.optimal_shift_rpm_ranges[gear] = (blended_min, blended_max)
                                    else:
                                        self.optimal_shift_rpm_ranges[gear] = (new_min, new_max)
                                    
                                    logger.debug(f"📊 Updated optimal shift range for gear {gear}: {self.optimal_shift_rpm_ranges[gear]}")
        
        except Exception as e:
            logger.error(f"Error learning optimal shift points: {e}")
    
    def _analyze_weight_transfer(self, telemetry: Dict[str, Any]):
        """Analyze weight transfer and vehicle balance"""
        try:
            lat_accel = telemetry.get('latAccel', 0)  # Lateral G-force
            long_accel = telemetry.get('longAccel', 0)  # Longitudinal G-force
            current_time = time.time()
            speed = telemetry.get('speed', 0)
            brake = telemetry.get('brake', 0)
            throttle = telemetry.get('throttle', 0)
            
            # Calculate weight transfer based on G-forces
            # Longitudinal weight transfer (braking/acceleration)
            # Positive long_accel = acceleration (weight to rear)
            # Negative long_accel = braking (weight to front)
            longitudinal_transfer = long_accel  # Direct correlation
            
            # Lateral weight transfer (cornering)
            # Positive lat_accel = right turn (weight to left)
            # Negative lat_accel = left turn (weight to right)
            lateral_transfer = lat_accel
            
            # Estimate axle load distribution (simplified physics model)
            # Base distribution (typically 45% front, 55% rear for GT3)
            base_front_load = 0.45
            base_rear_load = 0.55
            
            # Weight transfer affects distribution
            # Under braking: more weight to front
            # Under acceleration: more weight to rear
            weight_transfer_factor = long_accel * 0.1  # Scale factor
            front_axle_load = base_front_load - weight_transfer_factor
            rear_axle_load = base_rear_load + weight_transfer_factor
            
            # Clamp values to realistic ranges
            front_axle_load = max(0.35, min(0.65, front_axle_load))
            rear_axle_load = 1.0 - front_axle_load
            
            # Calculate understeer gradient (simplified)
            # Higher front load relative to rear can increase understeer
            understeer_gradient = (front_axle_load - 0.45) * 2.0  # Normalized
            
            # Calculate grip utilization (how much of available grip is used)
            combined_g = np.sqrt(lat_accel**2 + long_accel**2)
            max_theoretical_g = 2.5  # Typical GT3 maximum
            grip_utilization = min(1.0, combined_g / max_theoretical_g)
            
            # Calculate stability margin (how close to limit)
            stability_margin = max(0.0, 1.0 - grip_utilization)
            
            # Calculate efficiency metrics
            braking_efficiency = 1.0  # Default
            if brake > 10 and speed > 20:
                # Braking efficiency based on G-force vs brake input
                expected_g = (brake / 100.0) * 1.5  # Expected G for brake input
                if abs(long_accel) > 0.1:
                    braking_efficiency = min(1.0, abs(long_accel) / expected_g)
            
            traction_efficiency = 1.0  # Default
            if throttle > 10 and speed > 20:
                # Traction efficiency based on G-force vs throttle input
                expected_g = (throttle / 100.0) * 1.2  # Expected G for throttle input
                if long_accel > 0.1:
                    traction_efficiency = min(1.0, long_accel / expected_g)
            
            # Create weight transfer analysis
            weight_analysis = WeightTransferAnalysis(
                timestamp=current_time,
                longitudinal_transfer=longitudinal_transfer,
                lateral_transfer=lateral_transfer,
                front_axle_load=front_axle_load,
                rear_axle_load=rear_axle_load,
                understeer_gradient=understeer_gradient,
                grip_utilization=grip_utilization,
                stability_margin=stability_margin,
                braking_efficiency=braking_efficiency,
                traction_efficiency=traction_efficiency
            )
            
            self.weight_transfer_history.append(weight_analysis)
            
        except Exception as e:
            logger.error(f"Error in weight transfer analysis: {e}")
    
    def _analyze_g_forces(self, telemetry: Dict[str, Any]):
        """Analyze G-forces and acceleration patterns"""
        try:
            lat_accel = telemetry.get('latAccel', 0)
            long_accel = telemetry.get('longAccel', 0)
            vert_accel = telemetry.get('vertAccel', 0)
            current_time = time.time()
            
            # Calculate combined G-force
            combined_g = np.sqrt(lat_accel**2 + long_accel**2)
            
            # Analyze G-force smoothness over recent samples
            g_force_smoothness = 1.0  # Default to smooth
            excessive_g_events = 0
            
            if len(self.g_force_history) > 5:
                # Get recent G-force values
                recent_combined_g = [analysis.peak_combined_g for analysis in list(self.g_force_history)[-5:]]
                recent_combined_g.append(combined_g)
                
                # Calculate smoothness (lower variance = smoother)
                g_variance = np.var(recent_combined_g)
                g_force_smoothness = max(0.0, 1.0 - (g_variance * 2.0))  # Scale factor
                
                # Count excessive G-force spikes
                for g in recent_combined_g:
                    if g > self.max_safe_lat_g:
                        excessive_g_events += 1
            
            # Calculate grip circle utilization
            # The "grip circle" represents maximum available grip
            max_lat_g = 2.5   # Typical GT3 lateral limit
            max_long_g = 2.0  # Typical GT3 longitudinal limit
            
            # Normalize G-forces to grip circle
            normalized_lat = lat_accel / max_lat_g
            normalized_long = long_accel / max_long_g
            grip_circle_utilization = min(1.0, np.sqrt(normalized_lat**2 + normalized_long**2))
            
            # Determine if G-forces are in optimal range
            optimal_g_range = (0.5 <= combined_g <= 2.0)  # Sweet spot for GT3 cars
            
            # Create G-force analysis
            g_analysis = GForceAnalysis(
                timestamp=current_time,
                peak_lat_g=abs(lat_accel),
                peak_long_g=abs(long_accel),
                peak_combined_g=combined_g,
                g_force_smoothness=g_force_smoothness,
                grip_circle_utilization=grip_circle_utilization,
                excessive_g_events=excessive_g_events,
                optimal_g_range=optimal_g_range
            )
            
            self.g_force_history.append(g_analysis)
            
        except Exception as e:
            logger.error(f"Error in G-force analysis: {e}")
    
    def _generate_gear_shift_coaching(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Generate coaching messages for gear shifting technique"""
        messages = []
        
        if len(self.gear_shift_history) < 3:
            return messages
        
        current_time = time.time()
        current_gear = telemetry.get('gear', 0)
        current_rpm = telemetry.get('rpm', 0)
        
        # Analyze recent gear shifts
        recent_shifts = [shift for shift in self.gear_shift_history 
                        if current_time - shift.timestamp < 30.0]  # Last 30 seconds
        
        if not recent_shifts:
            return messages
        
        # Check for suboptimal shift timing
        early_shifts = [s for s in recent_shifts 
                       if s.shift_type == "upshift" and s.optimal_shift_point_delta < -500]
        late_shifts = [s for s in recent_shifts 
                      if s.shift_type == "upshift" and s.optimal_shift_point_delta > 500]
        
        if len(early_shifts) >= 2:
            avg_delta = np.mean([abs(s.optimal_shift_point_delta) for s in early_shifts])
            messages.append(CoachingMessage(
                message=f"Shifting too early - try shifting {avg_delta:.0f} RPM higher for more power",
                category="gear_shifting",
                priority=6,
                confidence=80,
                data_source="shift_timing",
                improvement_potential=0.05
            ))
        
        if len(late_shifts) >= 2:
            avg_delta = np.mean([s.optimal_shift_point_delta for s in late_shifts])
            messages.append(CoachingMessage(
                message=f"Shifting too late - shift {avg_delta:.0f} RPM earlier to stay in power band",
                category="gear_shifting",
                priority=6,
                confidence=80,
                data_source="shift_timing",
                improvement_potential=0.03
            ))
        
        # Check for poor rev matching on downshifts
        downshifts = [s for s in recent_shifts if s.shift_type == "downshift"]
        poor_rev_matching = [s for s in downshifts if s.rev_matching_quality < 60]
        
        if len(poor_rev_matching) >= 2:
            avg_quality = np.mean([s.rev_matching_quality for s in poor_rev_matching])
            messages.append(CoachingMessage(
                message=f"Rev matching could improve - try blipping throttle on downshifts for smoother transitions",
                category="gear_shifting", 
                priority=5,
                confidence=75,
                data_source="rev_matching",
                improvement_potential=0.02
            ))
        
        # Check for missed engine braking opportunities
        missed_engine_braking = [s for s in downshifts 
                               if not s.engine_braking_utilized and s.brake_at_shift > 30]
        
        if len(missed_engine_braking) >= 2:
            messages.append(CoachingMessage(
                message="Use engine braking more - downshift earlier to help slow the car",
                category="gear_shifting",
                priority=4,
                confidence=70,
                data_source="engine_braking",
                improvement_potential=0.08
            ))
        
        # Real-time shift point coaching
        if current_gear in self.optimal_shift_rpm_ranges and current_rpm > 0:
            optimal_min, optimal_max = self.optimal_shift_rpm_ranges[current_gear]
            
            if current_rpm > optimal_max + 200:  # Significantly over optimal
                messages.append(CoachingMessage(
                    message=f"Shift up now - you're {current_rpm - optimal_max:.0f} RPM past optimal shift point",
                    category="gear_shifting",
                    priority=7,
                    confidence=85,
                    data_source="real_time_shift",
                    improvement_potential=0.02
                ))
        
        return messages
    
    def _generate_weight_transfer_coaching(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Generate coaching messages for weight transfer and vehicle balance"""
        messages = []
        
        if len(self.weight_transfer_history) < 10:
            return messages
        
        current_time = time.time()
        
        # Analyze recent weight transfer data
        recent_analysis = [analysis for analysis in self.weight_transfer_history 
                          if current_time - analysis.timestamp < 10.0]  # Last 10 seconds
        
        if not recent_analysis:
            return messages
        
        # Check for poor braking efficiency
        poor_braking = [a for a in recent_analysis if a.braking_efficiency < 0.7]
        if len(poor_braking) > len(recent_analysis) * 0.5:  # More than 50% poor braking
            avg_efficiency = np.mean([a.braking_efficiency for a in poor_braking])
            messages.append(CoachingMessage(
                message=f"Braking efficiency low ({avg_efficiency:.1%}) - try progressive braking for better weight transfer",
                category="weight_transfer",
                priority=6,
                confidence=75,
                data_source="braking_efficiency",
                improvement_potential=0.1
            ))
        
        # Check for poor traction efficiency
        poor_traction = [a for a in recent_analysis if a.traction_efficiency < 0.7]
        if len(poor_traction) > len(recent_analysis) * 0.5:
            avg_efficiency = np.mean([a.traction_efficiency for a in poor_traction])
            messages.append(CoachingMessage(
                message=f"Traction efficiency low ({avg_efficiency:.1%}) - smoother throttle application will help",
                category="weight_transfer",
                priority=6,
                confidence=75,
                data_source="traction_efficiency",
                improvement_potential=0.08
            ))
        
        # Check for excessive understeer tendency
        current_analysis = recent_analysis[-1] if recent_analysis else None
        if current_analysis and current_analysis.understeer_gradient > 0.3:
            messages.append(CoachingMessage(
                message="Weight distribution favoring understeer - try later braking or trail braking",
                category="weight_transfer",
                priority=5,
                confidence=70,
                data_source="understeer_gradient",
                improvement_potential=0.06
            ))
        
        # Check for low grip utilization (not using available grip)
        recent_grip_usage = [a.grip_utilization for a in recent_analysis]
        avg_grip_usage = np.mean(recent_grip_usage)
        
        if avg_grip_usage < 0.6:  # Less than 60% grip utilization
            messages.append(CoachingMessage(
                message=f"Only using {avg_grip_usage:.1%} of available grip - you can push harder",
                category="weight_transfer",
                priority=4,
                confidence=65,
                data_source="grip_utilization",
                improvement_potential=0.15
            ))
        
        # Check for very low stability margin (near limit)
        if current_analysis and current_analysis.stability_margin < 0.1:
            messages.append(CoachingMessage(
                message="Very close to grip limit - back off slightly for safety margin",
                category="weight_transfer",
                priority=8,
                confidence=90,
                data_source="stability_margin",
                improvement_potential=-0.05  # Negative = safety over speed
            ))
        
        return messages
    
    def _generate_g_force_coaching(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Generate coaching messages for G-force and acceleration patterns"""
        messages = []
        
        if len(self.g_force_history) < 5:
            return messages
        
        current_time = time.time()
        
        # Analyze recent G-force data
        recent_analysis = [analysis for analysis in self.g_force_history 
                          if current_time - analysis.timestamp < 5.0]  # Last 5 seconds
        
        if not recent_analysis:
            return messages
        
        current_analysis = recent_analysis[-1]
        
        # Check for excessive G-forces
        if current_analysis.excessive_g_events > 0:
            messages.append(CoachingMessage(
                message=f"Excessive G-forces detected - smooth out your inputs for better tire grip",
                category="g_forces",
                priority=7,
                confidence=85,
                data_source="excessive_g",
                improvement_potential=0.1
            ))
        
        # Check for poor G-force smoothness
        avg_smoothness = np.mean([a.g_force_smoothness for a in recent_analysis])
        if avg_smoothness < 0.6:
            messages.append(CoachingMessage(
                message=f"G-force transitions are rough ({avg_smoothness:.1%}) - focus on smoother inputs",
                category="g_forces",
                priority=6,
                confidence=80,
                data_source="g_smoothness",
                improvement_potential=0.08
            ))
        
        # Check grip circle utilization
        avg_grip_circle = np.mean([a.grip_circle_utilization for a in recent_analysis])
        
        if avg_grip_circle < 0.5:  # Less than 50% of grip circle used
            messages.append(CoachingMessage(
                message=f"Only using {avg_grip_circle:.1%} of grip circle - you can brake/accelerate harder",
                category="g_forces",
                priority=4,
                confidence=70,
                data_source="grip_circle",
                improvement_potential=0.12
            ))
        elif avg_grip_circle > 0.95:  # Very close to limit
            messages.append(CoachingMessage(
                message=f"Using {avg_grip_circle:.1%} of grip circle - excellent commitment!",
                category="g_forces",
                priority=2,
                confidence=85,
                data_source="grip_circle_positive"
            ))
        
        # Check if G-forces are in optimal range
        in_optimal_range = [a for a in recent_analysis if a.optimal_g_range]
        if len(in_optimal_range) < len(recent_analysis) * 0.3:  # Less than 30% in optimal range
            messages.append(CoachingMessage(
                message="G-forces often outside optimal range - focus on consistent 1-2G in corners",
                category="g_forces",
                priority=5,
                confidence=75,
                data_source="g_range",
                improvement_potential=0.06
            ))
        
        # Real-time G-force warnings
        if current_analysis.peak_combined_g > self.max_safe_lat_g:
            messages.append(CoachingMessage(
                message=f"High G-forces ({current_analysis.peak_combined_g:.1f}G) - ease off to prevent tire overheating",
                category="g_forces",
                priority=8,
                confidence=90,
                data_source="high_g_warning",
                improvement_potential=0.0
            ))
        
        return messages
    
    def _detect_positive_performance(self, telemetry: Dict[str, Any]) -> List[CoachingMessage]:
        """Detect and celebrate good driving techniques"""
        messages = []
        current_time = time.time()
        
        # Only give positive feedback every 15 seconds to avoid spam
        if current_time - self.last_positive_feedback < 15:
            return messages
            
        speed = telemetry.get('speed', 0)
        corner = self.current_corner
        
        # Track personal bests through corners
        if corner and speed > 30:  # Valid corner speed
            if corner not in self.corner_personal_bests or speed > self.corner_personal_bests[corner]:
                self.corner_personal_bests[corner] = speed
                messages.append(CoachingMessage(
                    message=f"🏆 Personal best through {corner}! Great technique!",
                    category="positive",
                    priority=7,
                    confidence=95,
                    data_source="personal_best"
                ))
                self.last_positive_feedback = current_time
        
        # Celebrate consistent lap times
        if len(self.laps) >= 3:
            recent_times = [lap.lap_time for lap in self.laps[-3:] if lap.lap_time > 0]
            if len(recent_times) == 3:
                consistency = np.std(recent_times) / np.mean(recent_times)
                if consistency < 0.01:  # Very consistent
                    messages.append(CoachingMessage(
                        message="🎯 Incredible consistency! Your lap times are within 0.1s!",
                        category="positive",
                        priority=6,
                        confidence=95,
                        data_source="consistency"
                    ))
                    self.last_positive_feedback = current_time
        
        return messages
    
    def _enhance_messages_with_llm(self, messages: List[CoachingMessage]) -> List[CoachingMessage]:
        """Enhance coaching messages with LLM natural language processing"""
        if not messages or not self.llm_client.enabled:
            return messages
        
        enhanced_messages = []
        context = self._build_llm_context()
        
        for message in messages:
            # Only enhance high-priority messages to avoid latency
            if message.priority >= 6:
                try:
                    llm_response = self.llm_client.enhance_coaching_message(message.message, context)
                    if llm_response.confidence > 0.3:  # Use enhanced version if confident
                        # Create enhanced message with explanation
                        enhanced_text = llm_response.enhanced_message
                        if llm_response.explanation:
                            enhanced_text += f" ({llm_response.explanation})"
                        
                        enhanced_message = CoachingMessage(
                            message=enhanced_text,
                            category=message.category + "_enhanced",
                            priority=message.priority,
                            confidence=message.confidence * llm_response.confidence,
                            data_source=message.data_source + "_llm",
                            improvement_potential=message.improvement_potential
                        )
                        enhanced_messages.append(enhanced_message)
                    else:
                        enhanced_messages.append(message)  # Use original if LLM not confident
                except Exception as e:
                    logger.warning(f"LLM enhancement failed for message: {e}")
                    enhanced_messages.append(message)  # Fallback to original
            else:
                enhanced_messages.append(message)  # Low priority - use original
        
        return enhanced_messages
    
    def generate_session_report(self) -> str:
        """Generate comprehensive session analysis with LLM insights"""
        context = self._build_llm_context()
        
        if self.llm_client.enabled:
            return self.llm_client.generate_session_analysis(context)
        else:
            # Fallback to basic session summary
            summary = self.get_session_summary()
            basic_report = f"""
Session Summary:
- Laps completed: {summary.get('laps_completed', 0)}
- Best lap time: {summary.get('best_lap_time', 'N/A')}
- Driving style: {summary.get('driving_style', 'unknown')}
- Consistency: {summary.get('consistency', 'N/A')}

Enable LLM integration for detailed analysis and personalized coaching advice.
"""
            return basic_report.strip()
    
    def _track_driving_issues(self, messages: List[CoachingMessage]):
        """Track current driving issues for LLM context"""
        for message in messages:
            if message.priority >= 7:  # High priority issues
                issue = f"{message.category}:{message.data_source}"
                if issue not in self.current_issues:
                    self.current_issues.append(issue)
    
    def _track_improvements(self, messages: List[CoachingMessage]):
        """Track improvements for positive reinforcement"""
        for message in messages:
            if message.category == "positive" or "excellent" in message.message.lower():
                improvement = f"{message.category}:{message.data_source}"
                if improvement not in self.recent_improvements:
                    self.recent_improvements.append(improvement)

# Example usage with LLM integration:
"""
# Basic usage (fast system only)
coach = LocalAICoach()
messages = coach.process_telemetry(telemetry_data)

# Enhanced usage with LLM
coach = LocalAICoach()
coach.enable_llm_coaching(model="llama3.1:8b")  # or "phi-3-mini" for faster responses
coach.set_communication_style("supportive")      # "technical", "motivational", "balanced"

# Process telemetry (now with enhanced messages)
enhanced_messages = coach.process_telemetry(telemetry_data)

# Generate session report
session_analysis = coach.generate_session_report()
print(session_analysis)
"""
