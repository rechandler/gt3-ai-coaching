#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid Coaching Agent
Combines local ML analysis with remote AI coaching
"""

import asyncio
import time
import logging
import inspect
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum

# Import components
from local_ml_coach import LocalMLCoach
from remote_ai_coach import RemoteAICoach
from message_queue import CoachingMessageQueue, MessagePriority, CoachingMessage
from telemetry_analyzer import TelemetryAnalyzer
from session_manager import SessionManager
from track_metadata_manager import TrackMetadataManager
from segment_analyzer import SegmentAnalyzer
from rich_context_builder import RichContextBuilder, EventContext
from reference_manager import ReferenceManager
from micro_analysis import MicroAnalyzer, ReferenceDataManager
from mistake_tracker import MistakeTracker, SessionSummary
from lap_buffer_manager import LapBufferManager
from enhanced_context_builder import EnhancedContextBuilder
from schema_validator import SchemaValidator, ValidationResult
from reference_lap_helper import ReferenceLapHelper, create_reference_lap_helper

logger = logging.getLogger(__name__)

class CoachingMode(Enum):
    """Coaching modes"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    RACE = "race"

class DecisionEngine:
    """Makes decisions about when to use AI vs local coaching"""
    
    def __init__(self):
        self.ai_usage_count = []
        self.last_ai_decision = 0
        self.ai_usage_threshold = 0.3  # 30% of requests can use AI
    
    def should_use_ai(self, insight: Dict[str, Any], local_confidence: float) -> bool:
        """Always use AI coaching for all insights/messages"""
        return True

@dataclass
class CoachingContext:
    """Current coaching context"""
    track_name: str = ""
    car_name: str = ""
    category: str = ""  # Added category field
    session_type: str = ""
    lap_count: int = 0
    best_lap_time: float = 0.0
    current_position: int = 0
    total_cars: int = 0
    weather_conditions: str = ""
    tire_condition: str = ""
    fuel_level: float = 0.0
    coaching_mode: CoachingMode = CoachingMode.INTERMEDIATE

    def update_from_session_state(self, session_state):
        """Update context fields from a SessionState object."""
        self.track_name = getattr(session_state, 'track_name', self.track_name)
        self.car_name = getattr(session_state, 'car_name', self.car_name)
        self.category = getattr(session_state, 'category', self.category)
        self.session_type = getattr(session_state, 'session_type', self.session_type)
        self.coaching_mode = getattr(session_state, 'coaching_mode', self.coaching_mode)

class HybridCoachingAgent:
    """Hybrid coaching agent combining local ML and remote AI"""
    LLM_DEBOUNCE_SECONDS = 1.0

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.context = CoachingContext()
        
        # Initialize components
        self.local_coach = LocalMLCoach(config.get('local_config', {}))
        self.remote_coach = RemoteAICoach(config.get('remote_config', {}))
        self.message_queue = CoachingMessageQueue(config)
        self.telemetry_analyzer = TelemetryAnalyzer()
        self.session_manager = SessionManager()
        self.decision_engine = DecisionEngine()
        
        # Initialize micro-analysis system
        self.reference_manager = ReferenceDataManager()
        self.micro_analyzer = MicroAnalyzer(self.reference_manager)
        
        # Initialize mistake tracker
        self.mistake_tracker = MistakeTracker()
        
        # Track metadata manager for segment-based analysis
        self.track_metadata_manager = TrackMetadataManager()
        self.segment_analyzer = SegmentAnalyzer(self.track_metadata_manager)
        
        # Rich context builder
        self.rich_context_builder = RichContextBuilder()
        
        # Reference manager for professional coaching comparisons
        self.reference_manager = ReferenceManager()
        
        # Lap buffer manager for accurate lap/sector tracking
        self.lap_buffer_manager = LapBufferManager()
        
        # Enhanced context builder for time-series analysis
        self.enhanced_context_builder = EnhancedContextBuilder(config.get('enhanced_context', {}))
        
        # Schema validator for data validation
        self.schema_validator = SchemaValidator()
        
        # Reference lap helper for lap comparisons
        self.reference_lap_helper = None  # Will be initialized when track info is available
        
        self.current_track_name = None
        self.current_segment = None
        
        # State tracking
        self.is_active = False
        self.last_telemetry_time = 0
        self.performance_metrics = defaultdict(list)
        self.llm_insight_buffer = []
        self.llm_debounce_task = None
        
        logger.info("Hybrid Coaching Agent initialized with enhanced systems")
    
    async def start(self):
        """Start the coaching agent"""
        self.is_active = True
        logger.info("Coaching agent started")

        # Always load segment metadata for the current track at session start
        track_name = getattr(self.context, 'track_name', None)
        if track_name:
            logger.info(f"Triggering segment metadata load for track: {track_name}")
            await self.track_metadata_manager.ensure_metadata_for_track(track_name, self.context)
        else:
            logger.warning("No track name set in context at session start; segment metadata not loaded.")

        # Check remote AI coach availability
        if self.remote_coach.is_available():
            logger.info("Remote AI coach is available and ready")
        else:
            logger.warning("Remote AI coach is not available - check API key configuration")
        
        # Start background tasks (don't await them - they run indefinitely)
        asyncio.create_task(self.message_processor())
        asyncio.create_task(self.performance_tracker())
        asyncio.create_task(self.session_monitor())
    
    async def stop(self):
        """Stop the coaching agent"""
        self.is_active = False
        self.session_manager.save_session()  # Do not await, as this is not async
        logger.info("Coaching agent stopped")
        return None
    
    async def process_telemetry(self, telemetry_data: Dict[str, Any]):
        """Process incoming telemetry data"""
        if not self.is_active:
            return
        
        try:
            # Debug: Log available telemetry fields (first time only)
            if not hasattr(self, '_logged_telemetry_fields'):
                logger.info(f"Available telemetry fields: {list(telemetry_data.keys())}")
                self._logged_telemetry_fields = True
            
            # Validate telemetry data using schema validator
            validation_result = self.schema_validator.validate_telemetry(telemetry_data)
            if not validation_result.is_valid:
                logger.warning(f"Telemetry validation failed: {validation_result.errors}")
                # Continue processing with original data, but log the issues
                telemetry_data = self.schema_validator.transform_legacy_telemetry(telemetry_data)
            
            # Update track metadata if needed
            track_name = telemetry_data.get('track_name')
            car_name = telemetry_data.get('car_name', 'Unknown Car')
            if track_name and track_name != self.current_track_name:
                await self.update_track_metadata(track_name)
                self.current_track_name = track_name
                
                # Initialize reference lap helper when track info is available
                if track_name and car_name and not self.reference_lap_helper:
                    self.reference_lap_helper = create_reference_lap_helper(self.lap_buffer_manager)
                    logger.info(f"Initialized reference lap helper for {track_name} - {car_name}")
            
            # Update lap buffer manager with track/car info
            if track_name and car_name:
                self.lap_buffer_manager.update_track_info(track_name, car_name)
            
            # Add telemetry to enhanced context builder for time-series analysis
            self.enhanced_context_builder.add_telemetry(telemetry_data)
            
            # Buffer telemetry for lap/sector analysis
            lap_event = self.lap_buffer_manager.buffer_telemetry(telemetry_data)
            if lap_event:
                logger.info(f"Lap event detected: {lap_event.get('type')}")
                await self.handle_lap_event(lap_event, telemetry_data)
            
            # Process through micro-analyzer for corner-specific feedback
            self.process_micro_analysis(telemetry_data)
            
            # Process through segment analyzer
            self.segment_analyzer.buffer_telemetry(telemetry_data)
            
            # Update sector boundaries from SplitTimeInfo if present
            split_time_info = telemetry_data.get('SplitTimeInfo')
            if split_time_info and 'Sectors' in split_time_info:
                # Extract sector start percentages and ensure sorted order
                sector_boundaries = [s['SectorStartPct'] for s in sorted(split_time_info['Sectors'], key=lambda x: x['SectorNum'])]
                # Ensure 1.0 is the final boundary if not already present
                if sector_boundaries[-1] < 1.0:
                    sector_boundaries.append(1.0)
                self.telemetry_analyzer.sector_analyzer.update_sector_boundaries(sector_boundaries)

            # Process through telemetry analyzer
            analysis = self.telemetry_analyzer.analyze(telemetry_data)

            # Inject computed lap/sector data into telemetry_data for prompt/rich context
            if analysis.get('lap'):
                lap_analysis = analysis['lap']
                telemetry_data['lapCurrentLapTime'] = lap_analysis.lap_time
                telemetry_data['lapBestLapTime'] = self.telemetry_analyzer.best_lap_time if hasattr(self.telemetry_analyzer, 'best_lap_time') else lap_analysis.lap_time
                telemetry_data['sector_times'] = lap_analysis.sector_times
            if analysis.get('sector'):
                sector_analysis = analysis['sector']
                telemetry_data['sector_deltas'] = sector_analysis.get('deltas', [])
            if analysis.get('lap') and hasattr(self.telemetry_analyzer, 'completed_laps'):
                # Delta to session best lap
                best_lap = min([lap.lap_time for lap in self.telemetry_analyzer.completed_laps]) if self.telemetry_analyzer.completed_laps else lap_analysis.lap_time
                telemetry_data['lapDeltaToSessionBestLap'] = lap_analysis.lap_time - best_lap
            
            # Get insights from local coach
            # Per user request, disable local ML coach insights for now.
            local_insights = []

            # Combine insights and generate coaching messages
            all_insights = local_insights.copy()
            
            # Add micro-analysis insights if available
            micro_insights = self.get_micro_analysis_insights()
            if micro_insights:
                logger.info(f"Adding {len(micro_insights)} micro-analysis insights")
                all_insights.extend(micro_insights)
            
            # Add enhanced context insights if available
            enhanced_insights = self.get_enhanced_context_insights(telemetry_data)
            if enhanced_insights:
                logger.info(f"Adding {len(enhanced_insights)} enhanced context insights")
                all_insights.extend(enhanced_insights)
            
            # Track mistakes based on combined insights
            self.track_mistakes(analysis, all_insights)

            # If no specific insights are found, do nothing. This prevents "General Feedback" spam.
            if not all_insights:
                return

            # Generate coaching messages from insights
            await self.generate_coaching_messages(all_insights, telemetry_data)
            
            # Update performance tracking
            self.update_performance_metrics(telemetry_data, analysis)
            
            # Store telemetry for session (using rich context builder)
            self.rich_context_builder.add_telemetry(telemetry_data)
            
        except Exception as e:
            logger.error(f"Error processing telemetry: {e}", exc_info=True)

    async def _debounce_and_flush_llm_buffer(self):
        try:
            logger.debug(f"Debounce timer started for {self.LLM_DEBOUNCE_SECONDS} seconds.")
            await asyncio.sleep(self.LLM_DEBOUNCE_SECONDS)
            await self.flush_llm_insight_buffer()
        except asyncio.CancelledError:
            logger.debug("Debounce task cancelled before flush.")
            pass

    async def flush_llm_insight_buffer(self):
        """Process all buffered insights with rich context and ML sub-advisor"""
        if not self.llm_insight_buffer:
            logger.debug("No insights to flush.")
            return
        
        logger.info(f"Flushing {len(self.llm_insight_buffer)} insights from buffer.")
        
        # Group insights by type for better context
        insight_groups = defaultdict(list)
        for insight, telemetry_data, current_segment in self.llm_insight_buffer:
            situation = insight.get('situation', 'general')
            insight_groups[situation].append((insight, telemetry_data, current_segment))
        
        logger.info(f"Grouped insights into {len(insight_groups)} categories: {list(insight_groups.keys())}")
        
        # Process each group
        for situation, group_insights in insight_groups.items():
            logger.info(f"Processing {len(group_insights)} insights for situation: {situation}")
            # Use the most recent telemetry data for context
            latest_telemetry = group_insights[-1][1]
            latest_segment = group_insights[-1][2]
            event_type = self._determine_event_type(situation)
            # Use rich context builder for advice context
            advice_context = self.rich_context_builder.build_structured_context(
                event_type=event_type,
                telemetry_data=latest_telemetry,
                context=self.context,
                current_segment=latest_segment,
                severity="medium"
            )
            # Process each insight in the group
            for insight, telemetry_data, current_segment in group_insights:
                await self.process_insight_with_advice_context(
                    insight, telemetry_data, current_segment, advice_context
                )
        
        # Clear the buffer
        self.llm_insight_buffer.clear()
        logger.info("LLM insight buffer flushed and cleared.")

    def _determine_event_type(self, situation: str) -> str:
        """Determine event type from situation"""
        situation_to_event = {
            'insufficient_braking': 'late_braking',
            'early_throttle_in_corners': 'early_throttle',
            'inconsistent_lap_times': 'inconsistency',
            'sector_analysis': 'sector_time_loss',
            'corner_analysis': 'corner_technique',
            'race_strategy': 'strategy',
            'understeer': 'understeer',
            'oversteer': 'oversteer',
            'offtrack': 'offtrack',
            'bad_exit': 'bad_exit',
            'missed_apex': 'missed_apex'
        }
        return situation_to_event.get(situation, 'general_technique')

    async def process_insight_with_advice_context(self, insight: Dict[str, Any], 
                                                  telemetry_data: Dict[str, Any],
                                                  current_segment: Optional[Dict[str, Any]],
                                                  advice_context: Dict[str, Any]):
        """Process a single insight with modular advice context"""
        situation = insight.get('situation', 'general')
        confidence = insight.get('confidence', 0.0)
        importance = insight.get('importance', 0.5)
        
        # Determine if we should use AI
        should_use_ai = self.decision_engine.should_use_ai(insight, confidence)
        
        logger.info(f"Processing insight: {situation}, confidence={confidence:.2f}, importance={importance:.2f}, should_use_ai={should_use_ai}")
        
        if should_use_ai and self.remote_coach.is_available():
            logger.info(f"Using AI for {situation}")
            # Use AI with advice context (rich context and ML analysis included)
            ai_response = await self.remote_coach.generate_coaching(
                insight, telemetry_data, self.context, 
                current_segment=current_segment,
                rich_context=None,  # Already included in advice_context if needed
                ml_analysis=advice_context.get('ml_analysis')
            )
            
            if ai_response:
                audio_data = ai_response.get('audio')
                if audio_data:
                    logger.info(f"AI generated audio: {len(audio_data)} chars")
                else:
                    logger.info("No audio generated by AI")
                    
                message = CoachingMessage(
                    content=ai_response['message'],
                    category=ai_response.get('category', 'ai_coaching'),
                    priority=MessagePriority.from_importance(importance),
                    source='remote_ai',
                    confidence=ai_response.get('confidence', 0.8),
                    context=situation,
                    timestamp=time.time(),
                    audio=audio_data  # Include audio data if present
                )
                await self.message_queue.add_message(message)
                
                # Track AI usage
                self.decision_engine.ai_usage_count.append(time.time())
                
                # Log rich context usage
                if ai_response.get('rich_context_used', False):
                    logger.info(f"AI coaching used rich context for {situation}")
            else:
                logger.warning(f"AI response was None for {situation}")
        else:
            if not should_use_ai:
                logger.info(f"Using local ML for {situation} (AI decision: {should_use_ai})")
            elif not self.remote_coach.is_available():
                logger.info(f"Using local ML for {situation} (AI not available)")
            
            # Use local ML response
            local_response = await self.local_coach.generate_message(insight)
            
            if local_response:
                message = CoachingMessage(
                    content=local_response['message'],
                    category=local_response.get('category', 'local_coaching'),
                    priority=MessagePriority.from_importance(importance),
                    source='local_ml',
                    confidence=confidence,
                    context=situation,
                    timestamp=time.time(),
                    audio=None  # Local ML doesn't generate audio
                )
                await self.message_queue.add_message(message)
            else:
                logger.warning(f"Local ML response was None for {situation}")
    
    async def message_processor(self):
        """Background task to process and deliver coaching messages"""
        while self.is_active:
            try:
                message = await self.message_queue.get_next_message()
                if message:
                    await self.deliver_message(message)
                    
                await asyncio.sleep(0.1)  # 10Hz processing
                
            except Exception as e:
                logger.error(f"Error in message processor: {e}")
                await asyncio.sleep(1)
    
    async def deliver_message(self, message: CoachingMessage):
        """Deliver a coaching message to the user"""
        try:
            # Format message for delivery
            formatted_message = {
                'type': 'coaching_message',
                'content': message.content,
                'category': message.category,
                'priority': message.priority.value,
                'source': message.source,
                'confidence': message.confidence,
                'timestamp': message.timestamp
            }
            
            # Send to UI (implement your delivery mechanism here)
            logger.info(f"Coaching: {message.content}")
            
            # Track message delivery
            self.performance_metrics['messages_delivered'].append(time.time())
            
        except Exception as e:
            logger.error(f"Error delivering message: {e}")
    
    async def send_segment_feedback(self, feedback: List[str]):
        """Send segment-based feedback to the user"""
        if not feedback or not self.segment_analyzer.should_send_feedback():
            return
            
        try:
            # Create coaching messages for each feedback item
            for feedback_item in feedback:
                message = CoachingMessage(
                    content=feedback_item,
                    category='segment_analysis',
                    priority=MessagePriority.MEDIUM,
                    source='segment_analyzer',
                    confidence=0.8,
                    context='segment_feedback',
                    timestamp=time.time(),
                    audio=None  # Segment feedback doesn't generate audio
                )
                await self.message_queue.add_message(message)
                
            logger.info(f"📊 Sent {len(feedback)} segment feedback items")
            
        except Exception as e:
            logger.error(f"Error sending segment feedback: {e}")
    
    async def performance_tracker(self):
        """Track coaching performance and effectiveness"""
        while self.is_active:
            try:
                # Track performance metrics
                current_time = time.time()
                
                # Calculate message rate
                recent_messages = len([
                    t for t in self.performance_metrics['messages_delivered']
                    if current_time - t < 60
                ])
                
                # Log performance stats every minute
                if int(current_time) % 60 == 0:
                    logger.info(f"Coaching stats - Messages/min: {recent_messages}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in performance tracker: {e}")
                await asyncio.sleep(5)
    
    async def session_monitor(self):
        """Monitor session and adapt coaching"""
        while self.is_active:
            try:
                # Update session data
                await self.session_manager.update_session(self.context)
                
                # Adapt coaching based on session progress
                await self.adapt_coaching_style()
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in session monitor: {e}")
                await asyncio.sleep(10)
    
    def update_context(self, telemetry_data: Dict[str, Any]):
        """Update coaching context from telemetry"""
        if 'track_name' in telemetry_data:
            self.context.track_name = telemetry_data['track_name']
        if 'car_name' in telemetry_data:
            self.context.car_name = telemetry_data['car_name']
        if 'session_type' in telemetry_data:
            self.context.session_type = telemetry_data['session_type']
        if 'lap_count' in telemetry_data:
            self.context.lap_count = telemetry_data['lap_count']
        if 'best_lap_time' in telemetry_data:
            self.context.best_lap_time = telemetry_data['best_lap_time']
    
    async def update_track_metadata(self, track_name: str):
        """Update track metadata for segment analysis"""
        try:
            logger.info(f"Updating track metadata for: {track_name}")
            segments = await self.track_metadata_manager.get_track_segments(track_name, self.context)
            if segments:
                self.segment_analyzer.update_track(track_name, segments)
                logger.info(f"Loaded {len(segments)} segments for {track_name}")
            else:
                logger.warning(f"No segments found for track: {track_name}")
        except Exception as e:
            logger.error(f"Error updating track metadata: {e}")
    
    def process_micro_analysis(self, telemetry_data: Dict[str, Any]):
        """Process telemetry through micro-analyzer"""
        try:
            # Get current segment for corner identification
            lap_dist_pct = telemetry_data.get('lapDistPct', telemetry_data.get('lap_distance_pct', 0))
            current_segment = self.segment_analyzer.get_current_segment(lap_dist_pct)
            
            logger.debug(f"Lap distance: {lap_dist_pct:.3f}, Current segment: {current_segment}")
            
            if current_segment and current_segment['type'] == 'corner':
                corner_id = f"{self.current_track_name}_{current_segment['name']}".replace(' ', '_').lower()
                logger.info(f"Processing corner: {current_segment['name']} (ID: {corner_id})")
                
                # Start or continue corner analysis
                if not self.micro_analyzer.current_corner_id:
                    self.micro_analyzer.start_corner_analysis(telemetry_data, corner_id)
                    logger.info(f"Started corner analysis for {corner_id}")
                else:
                    self.micro_analyzer.continue_corner_analysis(telemetry_data)
                    logger.debug(f"Continued corner analysis for {self.micro_analyzer.current_corner_id}")
            
        except Exception as e:
            logger.error(f"Error in micro-analysis: {e}")
    
    def get_micro_analysis_insights(self) -> List[Dict[str, Any]]:
        """Get insights from recent micro-analysis"""
        insights = []
        
        # Check if we have recent analysis
        if self.micro_analyzer.analysis_history:
            latest_analysis = self.micro_analyzer.analysis_history[-1]
            logger.debug(f"Latest micro-analysis: {latest_analysis.corner_name}, feedback count: {len(latest_analysis.specific_feedback)}")
            
            # Create insights from micro-analysis
            if latest_analysis.specific_feedback:
                insight = {
                    'type': 'micro_analysis',
                    'confidence': 0.9,  # High confidence for specific measurements
                    'severity': self.get_severity_from_priority(latest_analysis.priority),
                    'category': 'corner_technique',
                    'message': latest_analysis.specific_feedback[0],  # Use first feedback item
                    'data': {
                        'corner_id': latest_analysis.corner_id,
                        'corner_name': latest_analysis.corner_name,
                        'brake_timing_delta': latest_analysis.brake_timing_delta,
                        'throttle_timing_delta': latest_analysis.throttle_timing_delta,
                        'apex_speed_delta': latest_analysis.apex_speed_delta,
                        'total_time_loss': latest_analysis.total_time_loss,
                        'detected_patterns': latest_analysis.detected_patterns,
                        'all_feedback': latest_analysis.specific_feedback
                    }
                }
                insights.append(insight)
                logger.info(f"Generated micro-analysis insight for {latest_analysis.corner_name}")
        
        return insights
    
    def get_enhanced_context_insights(self, telemetry_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get insights from enhanced context builder time-series analysis"""
        insights = []
        
        try:
            # Get buffer stats to check if we have enough data
            buffer_stats = self.enhanced_context_builder.get_buffer_stats()
            # Use 'buffer_size' instead of 'total_samples'
            if buffer_stats.get('buffer_size', 0) < 10:  # Need at least 10 samples
                return insights
            # Analyze recent time-series data for patterns
            recent_data = list(self.enhanced_context_builder.telemetry_buffer)[-30:]  # Last 30 samples
            if len(recent_data) < 10:
                return insights
            # Analyze driver input consistency
            steering_angles = [point.steering_angle for point in recent_data]
            brake_inputs = [point.brake for point in recent_data]
            throttle_inputs = [point.throttle for point in recent_data]
            # Calculate consistency metrics
            steering_variance = self._calculate_variance(steering_angles)
            brake_variance = self._calculate_variance(brake_inputs)
            throttle_variance = self._calculate_variance(throttle_inputs)
            # Generate insights based on consistency
            if steering_variance > 0.1:  # High steering variance
                insight = {
                    'type': 'enhanced_context',
                    'confidence': 0.8,
                    'severity': 0.6,
                    'category': 'consistency',
                    'message': 'Steering input shows inconsistency - focus on smooth steering inputs',
                    'data': {
                        'steering_variance': steering_variance,
                        'analysis_type': 'time_series_consistency',
                        'time_window': '30_samples'
                    }
                }
                insights.append(insight)
            if brake_variance > 0.15:  # High brake variance
                insight = {
                    'type': 'enhanced_context',
                    'confidence': 0.85,
                    'severity': 0.7,
                    'category': 'braking_technique',
                    'message': 'Brake application is inconsistent - practice smooth brake modulation',
                    'data': {
                        'brake_variance': brake_variance,
                        'analysis_type': 'time_series_consistency',
                        'time_window': '30_samples'
                    }
                }
                insights.append(insight)
            # Analyze speed trends
            speeds = [point.speed_kph for point in recent_data]
            if len(speeds) > 5:
                speed_trend = self._calculate_trend(speeds)
                if speed_trend < -5:  # Significant speed decrease
                    insight = {
                        'type': 'enhanced_context',
                        'confidence': 0.75,
                        'severity': 0.5,
                        'category': 'speed_management',
                        'message': 'Speed is decreasing rapidly - check for early braking or missed apex',
                        'data': {
                            'speed_trend': speed_trend,
                            'analysis_type': 'speed_trend_analysis',
                            'time_window': '30_samples'
                        }
                    }
                    insights.append(insight)
        except KeyError as e:
            logger.error(f"Error getting enhanced context insights: missing key {e} in buffer_stats. Available keys: {list(buffer_stats.keys())}")
        except Exception as e:
            logger.error(f"Error getting enhanced context insights: {e}")
        
        return insights
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (slope) of values over time"""
        if len(values) < 2:
            return 0.0
        
        # Simple linear trend calculation
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * val for i, val in enumerate(values))
        x_squared_sum = sum(i * i for i in range(n))
        
        # Calculate slope
        slope = (n * xy_sum - x_sum * y_sum) / (n * x_squared_sum - x_sum * x_sum)
        return slope
    
    def get_severity_from_priority(self, priority: str) -> float:
        """Convert priority to severity score"""
        priority_map = {
            'critical': 0.9,
            'high': 0.7,
            'medium': 0.5,
            'low': 0.3
        }
        return priority_map.get(priority, 0.5)

    async def generate_coaching_messages(self, insights: List[Dict[str, Any]], telemetry_data: Dict[str, Any]):
        """Generate coaching messages from insights using LLM debouncing"""
        if not insights:
            logger.debug("No insights to process")
            return
        
        logger.info(f"Processing {len(insights)} insights for LLM buffering")
        
        # Get current segment information
        current_segment = self.segment_analyzer.get_current_segment(
            telemetry_data.get('lap_distance_pct', 0)
        )
        
        # Buffer insights for LLM processing
        for insight in insights:
            situation = insight.get('situation', 'unknown')
            confidence = insight.get('confidence', 0.0)
            importance = insight.get('importance', 0.5)
            logger.info(f"Buffering insight: {situation}, confidence={confidence:.2f}, importance={importance:.2f}")
            self.llm_insight_buffer.append((insight, telemetry_data, current_segment))
        
        logger.info(f"Buffered {len(insights)} insights for LLM processing. Buffer size: {len(self.llm_insight_buffer)}")
        
        # Start debounce timer if not already running
        if self.llm_debounce_task is None or self.llm_debounce_task.done():
            self.llm_debounce_task = asyncio.create_task(self._debounce_and_flush_llm_buffer())
            logger.info("Started LLM debounce timer")
        else:
            logger.debug("LLM debounce timer already running")
    
    def update_performance_metrics(self, telemetry_data: Dict[str, Any], analysis: Dict[str, Any]):
        """Update performance metrics based on telemetry and analysis"""
        # This is a placeholder. In a real scenario, you'd track specific metrics
        # like lap time, position, fuel, tire wear, etc.
        self.performance_metrics['last_lap_time'].append(telemetry_data.get('lapTime'))
        self.performance_metrics['current_position'].append(telemetry_data.get('currentPosition'))
        self.performance_metrics['fuel_level'].append(telemetry_data.get('fuelLevel'))
        self.performance_metrics['tire_condition'].append(telemetry_data.get('tireCondition'))
        self.performance_metrics['weather_conditions'].append(telemetry_data.get('weatherConditions'))
    
    async def adapt_coaching_style(self):
        """Adapt coaching style based on session progress and user performance"""
        try:
            # Analyze recent performance
            recent_performance = self.session_manager.get_recent_performance()
            
            # Adjust coaching mode based on performance
            if recent_performance['improvement_rate'] > 0.02:  # 2% improvement
                # User is improving, be encouraging
                self.local_coach.set_tone('encouraging')
            elif recent_performance['consistency'] < 0.8:  # Low consistency
                # Focus on consistency
                self.local_coach.set_focus('consistency')
            
            # Adjust AI usage based on effectiveness
            ai_effectiveness = self.calculate_ai_effectiveness()
            # Note: AI usage adjustment logic can be implemented here based on effectiveness
                
        except Exception as e:
            logger.error(f"Error adapting coaching style: {e}")
    
    def calculate_ai_effectiveness(self) -> float:
        """Calculate effectiveness of AI coaching messages"""
        # Placeholder - implement based on user feedback or performance correlation
        return 0.75
    
    def set_coaching_mode(self, mode: CoachingMode):
        """Set the coaching mode"""
        self.context.coaching_mode = mode
        self.local_coach.set_mode(mode)
        self.remote_coach.set_mode(mode)
        logger.info(f"Coaching mode set to: {mode.value}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coaching agent statistics"""
        # Convert coaching_mode to string if present in context
        context_dict = self.context.__dict__.copy() if hasattr(self, 'context') else {}
        if 'coaching_mode' in context_dict and hasattr(context_dict['coaching_mode'], 'value'):
            context_dict['coaching_mode'] = context_dict['coaching_mode'].value
        return {
            'is_active': self.is_active,
            'total_messages': len(self.performance_metrics['messages_delivered']),
            'ai_usage_rate': len(self.decision_engine.ai_usage_count),
            'local_coach_stats': self.local_coach.get_stats(),
            'remote_coach_stats': self.remote_coach.get_stats(),
            'context': context_dict
        }

    def track_mistakes(self, analysis: Dict[str, Any], micro_insights: List[Dict[str, Any]]):
        """Track mistakes for persistent analysis"""
        try:
            # Get current corner information
            current_segment = self.segment_analyzer.get_current_segment(
                analysis.get('lap_distance_pct', 0)
            )
            
            corner_id = None
            corner_name = None
            
            if current_segment:
                corner_id = f"{self.current_track_name}_{current_segment['name']}".replace(' ', '_').lower()
                corner_name = current_segment['name']
            
            # Track mistakes from micro-analysis
            for insight in micro_insights:
                if insight.get('type') == 'micro_analysis':
                    data = insight.get('data', {})
                    if data.get('total_time_loss', 0) > 0.05:  # Only track significant mistakes
                        self.mistake_tracker.add_mistake(
                            analysis_data=data,
                            corner_id=corner_id or "unknown",
                            corner_name=corner_name or "Unknown Corner"
                        )
            
            # Track mistakes from general analysis
            if analysis.get('corner'):
                corner_analysis = analysis['corner']
                if corner_analysis.time_loss > 0.05:
                    self.mistake_tracker.add_mistake(
                        analysis_data={
                            'total_time_loss': corner_analysis.time_loss,
                            'brake_timing_delta': 0,  # Placeholder
                            'throttle_timing_delta': 0,  # Placeholder
                            'apex_speed_delta': 0,  # Placeholder
                            'detected_patterns': []
                        },
                        corner_id=corner_id or "unknown",
                        corner_name=corner_name or "Unknown Corner"
                    )
                    
        except Exception as e:
            logger.error(f"Error tracking mistakes: {e}")
    
    def get_persistent_mistakes(self) -> List[Dict[str, Any]]:
        """Get persistent mistakes for coaching focus"""
        persistent = self.mistake_tracker.get_persistent_mistakes()
        
        return [
            {
                'corner_name': pattern.corner_name,
                'mistake_type': pattern.mistake_type,
                'frequency': pattern.frequency,
                'total_time_loss': pattern.total_time_loss,
                'avg_time_loss': pattern.avg_time_loss,
                'priority': pattern.priority,
                'severity_trend': pattern.severity_trend,
                'description': pattern.description
            }
            for pattern in persistent
        ]
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary with persistent mistakes"""
        summary = self.mistake_tracker.get_session_summary()
        
        return {
            'session_id': summary.session_id,
            'session_duration': summary.session_end - summary.session_start,
            'total_mistakes': summary.total_mistakes,
            'total_time_lost': summary.total_time_lost,
            'session_score': summary.session_score,
            'most_common_mistakes': [
                {
                    'corner_name': pattern.corner_name,
                    'mistake_type': pattern.mistake_type,
                    'frequency': pattern.frequency,
                    'total_time_loss': pattern.total_time_loss,
                    'description': pattern.description
                }
                for pattern in summary.most_common_mistakes
            ],
            'most_costly_mistakes': [
                {
                    'corner_name': pattern.corner_name,
                    'mistake_type': pattern.mistake_type,
                    'frequency': pattern.frequency,
                    'total_time_loss': pattern.total_time_loss,
                    'description': pattern.description
                }
                for pattern in summary.most_costly_mistakes
            ],
            'improvement_areas': summary.improvement_areas,
            'recommendations': summary.recommendations
        }
    
    def get_corner_analysis(self, corner_id: str) -> Dict[str, Any]:
        """Get detailed analysis for a specific corner"""
        return self.mistake_tracker.get_corner_analysis(corner_id)
    
    async def handle_lap_event(self, lap_event: Dict[str, Any], telemetry_data: Dict[str, Any]):
        """Handle lap completion or sector events"""
        try:
            event_type = lap_event.get('type')
            
            if event_type == 'lap_completed':
                lap_data = lap_event.get('lap_data')
                if lap_data is None:
                    logger.warning("Lap completed event received but no lap data")
                    return
                    
                is_personal_best = lap_event.get('is_personal_best', False)
                is_session_best = lap_event.get('is_session_best', False)
                
                # Create coaching message for lap completion
                message_content = f"🏁 Lap {lap_data.lap_number} completed: {lap_data.lap_time:.3f}s"
                
                if is_personal_best:
                    message_content += " 🏆 NEW PERSONAL BEST!"
                elif is_session_best:
                    message_content += " 🥇 New session best!"
                
                # Add sector analysis if available
                if lap_data.sector_times:
                    sector_times = [f"{t:.3f}s" for t in lap_data.sector_times]
                    message_content += f" Sectors: {' | '.join(sector_times)}"
                
                # Queue the message
                coaching_message = CoachingMessage(
                    content=message_content,
                    category="lap_timing",
                    priority=MessagePriority.HIGH if is_personal_best else MessagePriority.MEDIUM,
                    source="lap_buffer",
                    confidence=1.0,
                    context="lap_completion",
                    timestamp=time.time(),
                    audio=None  # Lap timing doesn't generate audio
                )
                await self.message_queue.add_message(coaching_message)
                
                # --- General feedback message (improvements, mistakes, positives) ---
                # Get session summary from mistake tracker
                summary = self.mistake_tracker.get_session_summary()
                improvement_areas = summary.improvement_areas
                recommendations = summary.recommendations
                most_costly = summary.most_costly_mistakes
                positives = []
                if summary.session_score > 0.8:
                    positives.append("Great consistency and low mistake rate!")
                elif summary.session_score > 0.6:
                    positives.append("Good session, but some areas to improve.")
                else:
                    positives.append("Session had some challenges, but keep pushing!")
                # Build feedback message
                feedback_lines = []
                if improvement_areas:
                    feedback_lines.append("Improvements: " + "; ".join(improvement_areas))
                if most_costly:
                    costly = [f"{m.corner_name}: {m.description} ({m.time_loss:.1f}s lost)" for m in most_costly]
                    feedback_lines.append("Key mistakes: " + "; ".join(costly))
                if recommendations:
                    feedback_lines.append("Advice: " + "; ".join(recommendations))
                if positives:
                    feedback_lines.append("Positives: " + "; ".join(positives))
                if feedback_lines:
                    feedback_message = CoachingMessage(
                        content="Lap Feedback: " + " | ".join(feedback_lines),
                        category="lap_feedback",
                        priority=MessagePriority.MEDIUM,
                        source="lap_feedback",
                        confidence=1.0,
                        context="lap_feedback",
                        timestamp=time.time(),
                        audio=None
                    )
                    await self.message_queue.add_message(feedback_message)
                # --- End general feedback message ---
                
                # Update session manager
                self.session_manager.add_lap_data(
                    lap_data.lap_time,
                    lap_data.sector_times,
                    {'telemetry_count': len(lap_data.telemetry_points)}
                )
                
                logger.info(f"Lap completed: {lap_data.lap_time:.3f}s")
            
            elif event_type == 'sector_completed':
                sector_data = lap_event.get('sector_data')
                if sector_data is None:
                    logger.warning("Sector completed event received but no sector data")
                    return
                    
                is_best_sector = lap_event.get('is_best_sector', False)
                is_session_best_sector = lap_event.get('is_session_best_sector', False)
                
                # Create sector completion message
                message_content = f"📊 Sector {sector_data.sector_number + 1}: {sector_data.sector_time:.3f}s"
                
                if is_best_sector:
                    message_content += " 🏆 Best sector!"
                elif is_session_best_sector:
                    message_content += " 🥇 Session best sector!"
                
                # Queue the message
                coaching_message = CoachingMessage(
                    content=message_content,
                    category="sector_timing",
                    priority=MessagePriority.MEDIUM,
                    source="lap_buffer",
                    confidence=1.0,
                    context="sector_completion",
                    timestamp=time.time(),
                    audio=None  # Sector timing doesn't generate audio
                )
                await self.message_queue.add_message(coaching_message)
                
                # --- General sector feedback ---
                # Use segment analyzer to get feedback for this sector if available
                feedback_lines = []
                if hasattr(self, 'segment_analyzer') and self.segment_analyzer:
                    # Try to get feedback for the sector (segment)
                    seg_feedback = []
                    if hasattr(self.segment_analyzer, 'generate_segment_feedback'):
                        # Find the segment info
                        if hasattr(self.segment_analyzer, 'track_segments') and self.segment_analyzer.track_segments:
                            seg_idx = sector_data.sector_number
                            if seg_idx < len(self.segment_analyzer.track_segments):
                                segment = self.segment_analyzer.track_segments[seg_idx]
                                # Use last metrics if available
                                if hasattr(self.segment_analyzer, 'best_lap_segments') and self.segment_analyzer.best_lap_segments:
                                    metrics = self.segment_analyzer.best_lap_segments.get(segment['name'], {})
                                    seg_feedback = self.segment_analyzer.generate_segment_feedback(segment, metrics)
                    if seg_feedback:
                        feedback_lines.extend(seg_feedback)
                if feedback_lines:
                    feedback_message = CoachingMessage(
                        content="Sector Feedback: " + " | ".join(feedback_lines),
                        category="sector_feedback",
                        priority=MessagePriority.MEDIUM,
                        source="sector_feedback",
                        confidence=1.0,
                        context="sector_feedback",
                        timestamp=time.time(),
                        audio=None
                    )
                    await self.message_queue.add_message(feedback_message)
                # --- End general sector feedback ---
                
                logger.info(f"Sector {sector_data.sector_number + 1} completed: {sector_data.sector_time:.3f}s")
                
        except Exception as e:
            logger.error(f"Error handling lap event: {e}")
    
    def get_recent_mistakes(self, window_minutes: int = 10) -> List[Dict[str, Any]]:
        """Get recent mistakes from time window"""
        recent_mistakes = self.mistake_tracker.get_recent_mistakes(window_minutes)
        
        return [
            {
                'corner_name': mistake.corner_name,
                'mistake_type': mistake.mistake_type,
                'time_loss': mistake.time_loss,
                'severity': mistake.severity,
                'description': mistake.description,
                'timestamp': mistake.timestamp
            }
            for mistake in recent_mistakes
        ]

async def maybe_await(result):
    if inspect.isawaitable(result):
        return await result
    return result

# Main entry point
async def main():
    """Main entry point for the coaching agent"""
    config = {
        'local_config': {
            'model_path': 'models/',
            'confidence_threshold': 0.7
        },
        'remote_config': {
            'api_key': 'your-openai-api-key',
            'model': 'gpt-3.5-turbo',
            'max_requests_per_minute': 5
        },
        'coaching_config': {
            'enable_local_coaching': True,
            'enable_ai_coaching': True
        }
    }
    
    agent = HybridCoachingAgent(config)
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Shutting down coaching agent...")
        await agent.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
