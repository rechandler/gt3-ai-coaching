#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coaching Message Queue System
Manages prioritization and delivery of coaching messages
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import heapq

logger = logging.getLogger(__name__)

class MessagePriority(Enum):
    """Message priority levels"""
    CRITICAL = 1    # Immediate safety concerns
    HIGH = 2        # Important technique corrections
    MEDIUM = 3      # General improvements
    LOW = 4         # Informational
    
    @classmethod
    def from_importance(cls, importance: float):
        """Convert importance score to priority"""
        if importance > 0.9:
            return cls.CRITICAL
        elif importance > 0.7:
            return cls.HIGH
        elif importance > 0.4:
            return cls.MEDIUM
        else:
            return cls.LOW

@dataclass
class CoachingMessage:
    """A coaching message with metadata"""
    content: str
    category: str
    priority: MessagePriority
    source: str  # 'local_ml' or 'remote_ai'
    confidence: float
    context: str
    timestamp: float
    delivered: bool = False
    attempts: int = 0
    
    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value < other.priority.value

class MessageFilter:
    """Filters duplicate and redundant messages"""
    
    def __init__(self):
        self.recent_messages = deque(maxlen=50)
        self.category_cooldowns = {}
        self.default_cooldown = 10.0  # seconds
        
        # Category-specific cooldowns
        self.category_cooldowns = {
            'braking': 8.0,
            'cornering': 12.0,
            'throttle': 6.0,
            'racing_line': 15.0,
            'safety': 2.0,  # Safety messages have short cooldown
            'pit_strategy': 30.0,
            'tire_management': 20.0
        }
    
    def should_deliver(self, message: CoachingMessage) -> bool:
        """Check if message should be delivered"""
        current_time = time.time()
        
        # Check for recent similar messages
        for recent_msg in self.recent_messages:
            if self.is_similar(message, recent_msg):
                cooldown = self.category_cooldowns.get(
                    message.category, self.default_cooldown
                )
                if current_time - recent_msg.timestamp < cooldown:
                    return False
        
        return True
    
    def is_similar(self, msg1: CoachingMessage, msg2: CoachingMessage) -> bool:
        """Check if two messages are similar"""
        # Same category
        if msg1.category == msg2.category:
            # Check content similarity (simple word overlap)
            words1 = set(msg1.content.lower().split())
            words2 = set(msg2.content.lower().split())
            overlap = len(words1.intersection(words2)) / len(words1.union(words2))
            if overlap > 0.6:  # 60% word overlap
                return True
        
        return False
    
    def add_delivered_message(self, message: CoachingMessage):
        """Add a delivered message to the filter"""
        message.timestamp = time.time()
        self.recent_messages.append(message)

class CoachingMessageQueue:
    """Priority queue for coaching messages"""
    
    def __init__(self):
        self.queue = []
        self.filter = MessageFilter()
        self.lock = asyncio.Lock()
        self.delivery_stats = {
            'total_added': 0,
            'total_delivered': 0,
            'filtered_duplicates': 0,
            'delivery_failures': 0
        }
        
        logger.info("Coaching message queue initialized")
    
    async def add_message(self, message: CoachingMessage):
        """Add a message to the queue"""
        async with self.lock:
            self.delivery_stats['total_added'] += 1
            
            # Check if message should be filtered
            if not self.filter.should_deliver(message):
                self.delivery_stats['filtered_duplicates'] += 1
                logger.debug(f"Filtered duplicate message: {message.category}")
                return False
            
            # Add to priority queue
            heapq.heappush(self.queue, message)
            logger.debug(f"Added message to queue: {message.category} (priority: {message.priority.name})")
            return True
    
    async def get_next_message(self) -> Optional[CoachingMessage]:
        """Get the next highest priority message"""
        async with self.lock:
            if not self.queue:
                return None
            
            message = heapq.heappop(self.queue)
            
            # Final delivery check
            if self.filter.should_deliver(message):
                self.filter.add_delivered_message(message)
                self.delivery_stats['total_delivered'] += 1
                return message
            else:
                # Message filtered at delivery time
                self.delivery_stats['filtered_duplicates'] += 1
                return None
    
    async def clear_queue(self):
        """Clear all messages from the queue"""
        async with self.lock:
            self.queue.clear()
            logger.info("Message queue cleared")
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get delivery statistics"""
        return {
            'queue_size': len(self.queue),
            'delivery_rate': (
                self.delivery_stats['total_delivered'] / 
                max(1, self.delivery_stats['total_added'])
            ),
            **self.delivery_stats
        }

class MessageTemplates:
    """Templates for common coaching messages"""
    
    TEMPLATES = {
        'braking': {
            'late_braking': "Brake earlier for turn {turn}. You're braking {distance}m too late.",
            'early_braking': "You can brake later for turn {turn}. Try braking {distance}m later.",
            'brake_pressure': "Increase brake pressure - you're at {current}% when you could use {optimal}%.",
            'brake_release': "Release brakes gradually as you turn in for better balance."
        },
        'cornering': {
            'apex_early': "You're hitting the apex too early in turn {turn}. Aim for a later apex.",
            'apex_late': "You're missing the apex in turn {turn}. Turn in earlier.",
            'exit_speed': "Focus on exit speed in turn {turn}. You're losing {time}s on corner exit.",
            'racing_line': "Try a different line through turn {turn} - aim for the inside/outside."
        },
        'throttle': {
            'early_throttle': "You can get on throttle earlier in turn {turn}.",
            'aggressive_throttle': "Ease into the throttle more gradually to avoid wheelspin.",
            'lift_throttle': "Small throttle lift through turn {turn} will help with balance."
        },
        'sector_analysis': {
            'sector_slow': "You're losing time in sector {sector}. Focus on {area}.",
            'sector_improvement': "Great improvement in sector {sector}! You gained {time}s.",
            'consistency': "Work on consistency - your lap times vary by {variation}s."
        }
    }
    
    @classmethod
    def get_template(cls, category: str, template_type: str, **kwargs) -> str:
        """Get a formatted template message"""
        try:
            template = cls.TEMPLATES[category][template_type]
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return f"Coaching advice for {category}: {template_type}"
    
    @classmethod
    def create_custom_message(cls, category: str, message: str, 
                            priority: MessagePriority = MessagePriority.MEDIUM,
                            source: str = 'template') -> CoachingMessage:
        """Create a coaching message from template"""
        return CoachingMessage(
            content=message,
            category=category,
            priority=priority,
            source=source,
            confidence=0.8,
            context='template',
            timestamp=time.time()
        )

# Example usage and testing
async def test_message_queue():
    """Test the message queue system"""
    queue = CoachingMessageQueue()
    
    # Create test messages
    messages = [
        CoachingMessage(
            content="Brake earlier for turn 1",
            category="braking",
            priority=MessagePriority.HIGH,
            source="local_ml",
            confidence=0.9,
            context="corner_entry",
            timestamp=time.time()
        ),
        CoachingMessage(
            content="Great lap time improvement!",
            category="encouragement",
            priority=MessagePriority.LOW,
            source="local_ml",
            confidence=0.8,
            context="lap_completion",
            timestamp=time.time()
        ),
        CoachingMessage(
            content="Safety concern: Car ahead braking",
            category="safety",
            priority=MessagePriority.CRITICAL,
            source="local_ml",
            confidence=1.0,
            context="following",
            timestamp=time.time()
        )
    ]
    
    # Add messages
    for msg in messages:
        await queue.add_message(msg)
    
    # Process messages (should come out in priority order)
    while queue.get_queue_size() > 0:
        msg = await queue.get_next_message()
        if msg:
            print(f"Delivered: {msg.priority.name} - {msg.content}")
        await asyncio.sleep(0.1)
    
    # Print stats
    print(f"Queue stats: {queue.get_stats()}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(test_message_queue())
