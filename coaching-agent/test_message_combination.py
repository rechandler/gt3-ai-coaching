#!/usr/bin/env python3
"""
Test script for message combination functionality
"""

import asyncio
import time
import logging
from message_queue import CoachingMessageQueue, CoachingMessage, MessagePriority
from config import DEFAULT_CONFIG

# Set up logging
logging.basicConfig(level=logging.DEBUG)

async def test_message_combination():
    """Test the message combination functionality"""
    
    # Initialize message queue with configuration
    queue = CoachingMessageQueue(DEFAULT_CONFIG)
    
    print("Testing message combination...")
    
    # Create multiple similar throttle messages
    messages = [
        CoachingMessage(
            content="Focus on getting the car rotated before getting back on the throttle.",
            category="throttle",
            priority=MessagePriority.MEDIUM,
            source="local_ml",
            confidence=0.8,
            context="understeer",
            timestamp=time.time()
        ),
        CoachingMessage(
            content="Wait longer before applying throttle in corners for better balance.",
            category="throttle",
            priority=MessagePriority.MEDIUM,
            source="local_ml",
            confidence=0.85,
            context="understeer",
            timestamp=time.time() + 0.1
        ),
        CoachingMessage(
            content="Patience with throttle application will improve your corner exit speed.",
            category="throttle",
            priority=MessagePriority.MEDIUM,
            source="local_ml",
            confidence=0.9,
            context="understeer",
            timestamp=time.time() + 0.2
        )
    ]
    
    # Add messages to queue
    for i, message in enumerate(messages):
        print(f"Adding message {i+1}: {message.content[:50]}...")
        result = await queue.add_message(message)
        print(f"Message {i+1} added: {result}")
    
    # Check queue stats
    stats = queue.get_stats()
    print(f"\nQueue stats: {stats}")
    
    # Get all messages from queue to see what's there
    print("\nMessages in queue:")
    queue_size = queue.get_queue_size()
    for i in range(queue_size):
        message = await queue.get_next_message()
        if message:
            print(f"Message {i+1}: {message.content}")
            print(f"  Source: {message.source}")
            print(f"  Category: {message.category}")
            print(f"  Confidence: {message.confidence}")
    
    # Check final stats
    final_stats = queue.get_stats()
    print(f"\nFinal stats: {final_stats}")

if __name__ == "__main__":
    asyncio.run(test_message_combination()) 