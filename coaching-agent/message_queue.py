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
from config import DEFAULT_CONFIG

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
    audio: Optional[str] = None  # Base64 encoded audio data
    delivered: bool = False
    attempts: int = 0
    
    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value < other.priority.value

class MessageCombiner:
    """Combines similar messages into concise summaries"""
    
    def __init__(self, config: Dict[str, Any] = None):
        # Get configuration or use defaults
        message_config = config.get('message_config', {}) if config else {}
        combination_config = message_config.get('message_combination', {})
        
        self.combination_window = combination_config.get('combination_window', 3.0)
        self.min_keyword_matches = combination_config.get('min_keyword_matches', 2)
        self.max_combined_messages = combination_config.get('max_combined_messages', 5)
        self.enabled = combination_config.get('enabled', True)
        
        self.combination_patterns = {
            'throttle': {
                'keywords': ['throttle', 'patience', 'corner', 'exit', 'balance', 'understeer'],
                'combine_template': "Focus on throttle patience: {summary}",
                'summary_template': "Wait longer before applying throttle in corners for better balance and exit speed."
            },
            'braking': {
                'keywords': ['brake', 'earlier', 'later', 'pressure', 'timing', 'entry'],
                'combine_template': "Brake technique needs work: {summary}",
                'summary_template': "Focus on brake timing and pressure for better corner entry."
            },
            'cornering': {
                'keywords': ['corner', 'line', 'apex', 'entry', 'exit', 'technique'],
                'combine_template': "Corner technique improvement: {summary}",
                'summary_template': "Work on corner entry, apex, and exit technique for better lap times."
            },
            'consistency': {
                'keywords': ['consistency', 'smooth', 'input', 'technique', 'pattern'],
                'combine_template': "Consistency focus: {summary}",
                'summary_template': "Focus on smooth, consistent inputs for better lap times."
            }
        }
    
    def should_combine_messages(self, message1: CoachingMessage, message2: CoachingMessage) -> bool:
        """Check if two messages should be combined"""
        if not self.enabled:
            return False
            
        # Must be same category
        if message1.category != message2.category:
            return False
        
        # Must be within time window
        time_diff = abs(message1.timestamp - message2.timestamp)
        if time_diff > self.combination_window:
            return False
        
        # Check for similar content using keyword matching
        return self._has_similar_keywords(message1.content, message2.content, message1.category)
    
    def _has_similar_keywords(self, content1: str, content2: str, category: str) -> bool:
        """Check if two messages have similar keywords"""
        if category not in self.combination_patterns:
            return False
        
        keywords = self.combination_patterns[category]['keywords']
        content1_lower = content1.lower()
        content2_lower = content2.lower()
        
        # Count matching keywords
        matches1 = sum(1 for keyword in keywords if keyword in content1_lower)
        matches2 = sum(1 for keyword in keywords if keyword in content2_lower)
        
        # If both messages contain similar keywords, they're candidates for combination
        return matches1 >= self.min_keyword_matches and matches2 >= self.min_keyword_matches
    
    def combine_messages(self, messages: List[CoachingMessage]) -> CoachingMessage:
        """Combine multiple similar messages into one concise message"""
        if not messages:
            return None
        
        if len(messages) == 1:
            return messages[0]
        
        # Limit the number of messages to combine
        if len(messages) > self.max_combined_messages:
            messages = messages[:self.max_combined_messages]
        
        # Use the highest priority message as base
        base_message = max(messages, key=lambda m: m.priority.value)
        category = base_message.category
        
        # Create combined content
        if category in self.combination_patterns:
            pattern = self.combination_patterns[category]
            summary = pattern['summary_template']
            combined_content = pattern['combine_template'].format(summary=summary)
        else:
            # Generic combination
            combined_content = f"Multiple {category} improvements needed: Focus on technique consistency."
        
        # Calculate combined confidence (average)
        avg_confidence = sum(m.confidence for m in messages) / len(messages)
        
        # Use highest priority
        highest_priority = min(messages, key=lambda m: m.priority.value).priority
        
        # Combine audio if any message has it
        combined_audio = None
        for message in messages:
            if message.audio:
                combined_audio = message.audio
                break
        
        return CoachingMessage(
            content=combined_content,
            category=category,
            priority=highest_priority,
            source='combined',
            confidence=avg_confidence,
            context=f"combined_{category}",
            timestamp=time.time(),
            audio=combined_audio
        )

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
        # Always deliver remote_ai (LLM) messages
        if getattr(message, 'source', None) == 'remote_ai':
            return True
        current_time = time.time()
        # Check for recent similar messages (only for local_ml)
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
    """Queue for managing coaching messages with priority and deduplication"""
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.queue = []
        self.delivered_messages = deque(maxlen=100)
        self.filter = MessageFilter()
        self.combiner = MessageCombiner(config)
        self.logger = logging.getLogger(__name__)
        self.lock = asyncio.Lock()
        self.delivery_stats = {
            'total_added': 0,
            'total_delivered': 0,
            'filtered_duplicates': 0,
            'delivery_failures': 0,
            'messages_combined': 0
        }
        # Global message rate limit (messages per minute)
        self.global_rate_limit = DEFAULT_CONFIG['message_config'].get('global_message_rate_limit', 5)
        self.delivered_timestamps = []  # List of timestamps of delivered messages
        self.logger.info("Coaching message queue initialized with message combination")
    
    async def add_message(self, message: CoachingMessage):
        # Log every message, regardless of delivery
        self.logger.info(f"[LOG ALL] Queued message: [{message.category}] {message.content} (source={message.source}, confidence={message.confidence:.2f})")
        # Check for LLM (remote_ai) priority
        if message.source == 'remote_ai':
            # Remove any local_ml messages in the queue for the same category within 3s
            self.queue = [m for m in self.queue if not (m.category == message.category and m.source == 'local_ml' and abs(m.timestamp - message.timestamp) < 3.0)]
        elif message.source == 'local_ml':
            # If a remote_ai message for this category and time window exists, skip adding
            for m in self.queue:
                if m.category == message.category and m.source == 'remote_ai' and abs(m.timestamp - message.timestamp) < 3.0:
                    self.logger.info(f"[LOG ALL] Skipping local_ml message due to remote_ai priority: [{message.category}] {message.content}")
                    return
        # Normal queueing
        heapq.heappush(self.queue, message)
    
    async def _check_for_combination(self, new_message: CoachingMessage) -> Optional[CoachingMessage]:
        """Check if the new message can be combined with existing messages"""
        current_time = time.time()
        candidates = []
        
        # Find messages in the queue that could be combined
        for message in self.queue:
            if self.combiner.should_combine_messages(new_message, message):
                candidates.append(message)
        
        if candidates:
            # Add the new message to candidates
            candidates.append(new_message)
            return self.combiner.combine_messages(candidates)
        
        return None
    
    async def _replace_messages_with_combined(self, combined_message: CoachingMessage):
        """Replace the original messages with the combined message"""
        # Create a new queue without the messages that were combined
        new_queue = []
        for msg in self.queue:
            # Check if this message should be kept (not combined)
            should_keep = True
            for candidate in [combined_message]:  # This is the combined message
                if self.combiner.should_combine_messages(candidate, msg):
                    should_keep = False
                    break
            
            if should_keep:
                new_queue.append(msg)
        
        # Replace the queue with the filtered messages
        self.queue = new_queue
        
        # Add the combined message
        heapq.heappush(self.queue, combined_message)
    
    async def get_next_message(self) -> Optional[CoachingMessage]:
        """Get the next highest priority message, enforcing global rate limit (except for CRITICAL)"""
        async with self.lock:
            if not self.queue:
                return None
            # Peek at the next message
            message = self.queue[0]
            now = time.time()
            # Clean up old timestamps (older than 60s)
            self.delivered_timestamps = [t for t in self.delivered_timestamps if now - t < 60]
            # Enforce global rate limit for non-critical messages
            if message.priority.name != 'CRITICAL' and len(self.delivered_timestamps) >= self.global_rate_limit:
                self.logger.debug("Global message rate limit reached; skipping delivery of non-critical message.")
                return None
            # Pop and deliver the message
            message = heapq.heappop(self.queue)
            # Final delivery check
            if self.filter.should_deliver(message):
                self.filter.add_delivered_message(message)
                self.delivery_stats['total_delivered'] += 1
                if message.priority.name != 'CRITICAL':
                    self.delivered_timestamps.append(now)
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
            timestamp=time.time(),
            audio=None  # Template messages don't generate audio
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
