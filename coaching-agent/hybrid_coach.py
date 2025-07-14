#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid GT3 Coaching Agent
Combines local machine learning with remote AI for optimal coaching experience
"""

import asyncio
import logging
import time
import json
import numpy as np
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum

from local_ml_coach import LocalMLCoach
from remote_ai_coach import RemoteAICoach
from message_queue import CoachingMessageQueue, CoachingMessage, MessagePriority
from telemetry_analyzer import TelemetryAnalyzer
from session_manager import SessionManager

logger = logging.getLogger(__name__)

class CoachingMode(Enum):
    """Different coaching modes"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    RACE = "race"
    PRACTICE = "practice"

class DecisionEngine:
    """Decides when to use local ML vs remote AI"""
    
    def __init__(self):
        self.local_confidence_threshold = 0.8
        self.ai_usage_limit = 5  # messages per minute
        self.ai_usage_count = deque(maxlen=100)
        
    def should_use_ai(self, situation: str, local_confidence: float, 
                      message_importance: float) -> bool:
        """Determine if we should use remote AI for this situation"""
        
        # Always use local for high-confidence, low-importance messages
        if local_confidence > self.local_confidence_threshold and message_importance < 0.5:
            return False
            
        # Use AI for complex situations or low local confidence
        if situation in ["corner_analysis", "race_strategy", "technique_improvement"]:
            return True
            
        # Check AI usage rate limiting
        current_time = time.time()
        recent_usage = len([t for t in self.ai_usage_count if current_time - t < 60])
        
        if recent_usage >= self.ai_usage_limit:
            return False
            
        # Use AI for important messages with low confidence
        return local_confidence < 0.6 and message_importance > 0.7

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
    """Main coaching agent that orchestrates local ML and remote AI"""
    
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
        
        # State tracking
        self.is_active = False
        self.last_telemetry_time = 0
        self.performance_metrics = defaultdict(list)
        
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
        await self.session_manager.save_session()
        logger.info("Coaching agent stopped")
    
    async def process_telemetry(self, telemetry_data: Dict[str, Any]):
        """Process incoming telemetry data"""
        if not self.is_active:
            return
            
        try:
            # Update context
            self.update_context(telemetry_data)
            
            # Analyze telemetry
            analysis = self.telemetry_analyzer.analyze(telemetry_data)
            
            # Get local ML insights
            local_insights = await self.local_coach.analyze(telemetry_data, analysis)
            
            # Process each insight
            for insight in local_insights:
                await self.process_insight(insight, telemetry_data)
                
        except Exception as e:
            logger.error(f"Error processing telemetry: {e}")
    
    async def process_insight(self, insight: Dict[str, Any], telemetry_data: Dict[str, Any]):
        """Process a coaching insight and decide on response"""
        
        situation = insight.get('situation', 'general')
        confidence = insight.get('confidence', 0.0)
        importance = insight.get('importance', 0.5)
        
        # Decide whether to use local or remote processing
        use_ai = self.decision_engine.should_use_ai(situation, confidence, importance)
        
        if use_ai and self.remote_coach.is_available():
            # Use remote AI for sophisticated analysis
            ai_response = await self.remote_coach.generate_coaching(
                insight, telemetry_data, self.context
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
            if ai_effectiveness < 0.5:
                self.decision_engine.local_confidence_threshold = 0.7  # Use AI less
            else:
                self.decision_engine.local_confidence_threshold = 0.8  # Use AI more
                
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
        return {
            'is_active': self.is_active,
            'total_messages': len(self.performance_metrics['messages_delivered']),
            'ai_usage_rate': len(self.decision_engine.ai_usage_count),
            'local_coach_stats': self.local_coach.get_stats(),
            'remote_coach_stats': self.remote_coach.get_stats(),
            'context': self.context.__dict__
        }

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
