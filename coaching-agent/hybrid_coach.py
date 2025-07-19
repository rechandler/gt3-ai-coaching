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
        """Decide whether to use AI coaching"""
        current_time = time.time()
        
        # Clean old AI usage records (older than 1 hour)
        self.ai_usage_count = [t for t in self.ai_usage_count if current_time - t < 3600]
        
        # Check if we're within AI usage limits
        if len(self.ai_usage_count) / max(1, len(self.ai_usage_count) + 10) > self.ai_usage_threshold:
            return False
        
        # Use AI for high-importance, low-confidence insights
        importance = insight.get('importance', 0.5)
        message_importance = importance * insight.get('confidence', 0.5)
        
        # AI for complex situations or when local confidence is low
        if message_importance > 0.7 and local_confidence < 0.6:
            return True
        
        # AI for specific event types that benefit from rich context
        situation = insight.get('situation', '')
        ai_beneficial_situations = [
            'understeer', 'oversteer', 'offtrack', 'bad_exit', 
            'missed_apex', 'sector_analysis', 'race_strategy'
        ]
        
        if situation in ai_beneficial_situations and message_importance > 0.5:
            return True
        
        return False

@dataclass
class CoachingContext:
    """Current coaching context"""
    track_name: str = ""
    car_name: str = ""
    session_type: str = ""
    lap_count: int = 0
    best_lap_time: float = 0.0
    current_position: int = 0
    total_cars: int = 0
    weather_conditions: str = ""
    tire_condition: str = ""
    fuel_level: float = 0.0
    coaching_mode: CoachingMode = CoachingMode.INTERMEDIATE

class HybridCoachingAgent:
    """Hybrid coaching agent combining local ML and remote AI"""
    LLM_DEBOUNCE_SECONDS = 1.0

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.context = CoachingContext()
        
        # Initialize components
        self.local_coach = LocalMLCoach(config.get('local_config', {}))
        self.remote_coach = RemoteAICoach(config.get('remote_config', {}))
        self.message_queue = CoachingMessageQueue()
        self.telemetry_analyzer = TelemetryAnalyzer()
        self.session_manager = SessionManager()
        self.decision_engine = DecisionEngine()
        
        # Initialize micro-analysis system
        self.reference_manager = ReferenceDataManager()
        self.micro_analyzer = MicroAnalyzer(self.reference_manager)
        
        # Track metadata manager for segment-based analysis
        self.track_metadata_manager = TrackMetadataManager()
        self.segment_analyzer = SegmentAnalyzer(self.track_metadata_manager)
        
        # Rich context builder
        self.rich_context_builder = RichContextBuilder()
        
        # Reference manager for professional coaching comparisons
        self.reference_manager = ReferenceManager()
        
        self.current_track_name = None
        self.current_segment = None
        
        # State tracking
        self.is_active = False
        self.last_telemetry_time = 0
        self.performance_metrics = defaultdict(list)
        self.llm_insight_buffer = []
        self.llm_debounce_task = None
        
        logger.info("Hybrid Coaching Agent initialized")
    
    async def start(self):
        """Start the coaching agent"""
        self.is_active = True
        logger.info("Coaching agent started")
        
        # Start background tasks
        await asyncio.gather(
            self.message_processor(),
            self.performance_tracker(),
            self.session_monitor()
        )
    
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
            # Update track metadata if needed
            track_name = telemetry_data.get('track_name')
            if track_name and track_name != self.current_track_name:
                await self.update_track_metadata(track_name)
                self.current_track_name = track_name
            
            # Process through micro-analyzer for corner-specific feedback
            self.process_micro_analysis(telemetry_data)
            
            # Process through segment analyzer
            self.segment_analyzer.buffer_telemetry(telemetry_data)
            
            # Process through telemetry analyzer
            analysis = self.telemetry_analyzer.analyze(telemetry_data)
            
            # Get local ML insights
            local_insights = await self.local_coach.analyze(telemetry_data, analysis)
            
            # Combine insights and generate coaching messages
            all_insights = local_insights.copy()
            
            # Add micro-analysis insights if available
            micro_insights = self.get_micro_analysis_insights()
            if micro_insights:
                all_insights.extend(micro_insights)
            
            # Generate coaching messages
            if all_insights:
                await self.generate_coaching_messages(all_insights, telemetry_data)
            
            # Update performance tracking
            self.update_performance_metrics(telemetry_data, analysis)
            
            # Store telemetry for session (using rich context builder)
            self.rich_context_builder.add_telemetry(telemetry_data)
            
        except Exception as e:
            logger.error(f"Error processing telemetry: {e}")

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
        
        logger.debug(f"Flushing {len(self.llm_insight_buffer)} insights from buffer.")
        
        # Group insights by type for better context
        insight_groups = defaultdict(list)
        for insight, telemetry_data, current_segment in self.llm_insight_buffer:
            situation = insight.get('situation', 'general')
            insight_groups[situation].append((insight, telemetry_data, current_segment))
        
        # Process each group
        for situation, group_insights in insight_groups.items():
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
        logger.debug("LLM insight buffer flushed and cleared.")

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
        
        if should_use_ai and self.remote_coach.is_available():
            # Use AI with advice context (rich context and ML analysis included)
            ai_response = await self.remote_coach.generate_coaching(
                insight, telemetry_data, self.context, 
                current_segment=current_segment,
                rich_context=None,  # Already included in advice_context if needed
                ml_analysis=advice_context.get('ml_analysis')
            )
            
            if ai_response:
                message = CoachingMessage(
                    content=ai_response['message'],
                    category=ai_response.get('category', 'ai_coaching'),
                    priority=MessagePriority.from_importance(importance),
                    source='remote_ai',
                    confidence=ai_response.get('confidence', 0.8),
                    context=situation,
                    timestamp=time.time()
                )
                await self.message_queue.add_message(message)
                
                # Track AI usage
                self.decision_engine.ai_usage_count.append(time.time())
                
                # Log rich context usage
                if ai_response.get('rich_context_used', False):
                    logger.info(f"AI coaching used rich context for {situation}")
        else:
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
                    timestamp=time.time()
                )
                await self.message_queue.add_message(message)
    
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
                    timestamp=time.time()
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
        """Ensure metadata is loaded for the current track"""
        await self.track_metadata_manager.ensure_metadata_for_track(track_name, self.context)
        segments = await self.track_metadata_manager.get_track_metadata(track_name)
        if segments:
            self.segment_analyzer.update_track(track_name, segments)
    
    def process_micro_analysis(self, telemetry_data: Dict[str, Any]):
        """Process telemetry through micro-analyzer"""
        try:
            # Get current segment for corner identification
            lap_dist_pct = telemetry_data.get('lapDistPct', 0) # Changed from 'lap_distance_pct' to 'lapDistPct'
            current_segment = self.segment_analyzer.get_current_segment(lap_dist_pct)
            
            if current_segment and current_segment['type'] == 'corner':
                corner_id = f"{self.current_track_name}_{current_segment['name']}".replace(' ', '_').lower()
                
                # Start or continue corner analysis
                if not self.micro_analyzer.current_corner_id:
                    self.micro_analyzer.start_corner_analysis(telemetry_data, corner_id)
                else:
                    self.micro_analyzer.continue_corner_analysis(telemetry_data)
            
        except Exception as e:
            logger.error(f"Error in micro-analysis: {e}")
    
    def get_micro_analysis_insights(self) -> List[Dict[str, Any]]:
        """Get insights from recent micro-analysis"""
        insights = []
        
        # Check if we have recent analysis
        if self.micro_analyzer.analysis_history:
            latest_analysis = self.micro_analyzer.analysis_history[-1]
            
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
        
        return insights
    
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
        """Generate coaching messages from insights using LLM"""
        if not insights:
            return
        
        # Group insights by type for better context
        insight_groups = defaultdict(list)
        for insight in insights:
            situation = insight.get('situation', 'general')
            insight_groups[situation].append(insight)
        
        for situation, group_insights in insight_groups.items():
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
            for insight in group_insights:
                await self.process_insight_with_advice_context(
                    insight, latest_telemetry, latest_segment, advice_context
                )
    
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
