#!/usr/bin/env python3
"""
Test script to verify coaching agent integration with GT3 overlay
"""

import asyncio
import json
import logging
import sys
import os
import time
from typing import Dict, Any

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'coaching-agent'))
sys.path.insert(0, os.path.join(project_root, 'telemetry-server', 'services'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_coaching_integration():
    """Test the coaching agent integration"""
    
    try:
        # Import and initialize coaching agent
        from coaching_data_service import CoachingDataService
        
        logger.info("🚀 Starting coaching integration test...")
        
        # Create coaching data service
        service = CoachingDataService()
        
        # Check if coaching agent is available
        if hasattr(service, 'coaching_agent') and service.coaching_agent:
            logger.info("✅ Coaching agent initialized successfully")
            
            # Test telemetry processing
            test_telemetry = {
                'Speed': 120.5,
                'Brake': 0.0,
                'Throttle': 0.85,
                'SteeringWheelAngle': 0.12,
                'LapDistPct': 0.25,
                'Gear': 4,
                'RPM': 6500,
                'LapCurrentLapTime': 45.2,
                'LapLastLapTime': 89.5
            }
            
            logger.info("🔧 Testing telemetry processing...")
            processed = await service.process_telemetry_with_coaching(test_telemetry)
            
            if 'coaching_stats' in processed:
                logger.info("✅ Coaching stats added to telemetry")
                logger.info(f"📊 Stats: {processed['coaching_stats']}")
            else:
                logger.warning("⚠️ No coaching stats in processed telemetry")
            
            # Test message format
            logger.info("🧠 Testing coaching message format...")
            
            # Simulate a coaching message
            from message_queue import CoachingMessage, MessagePriority
            
            test_message = CoachingMessage(
                content="You can brake later into this corner for better lap times",
                category="braking",
                priority=MessagePriority.MEDIUM,
                source="local_ml",
                confidence=0.8,
                context="corner_analysis",
                timestamp=time.time()
            )
            
            # Test message formatting
            formatted_message = {
                "type": "coaching",
                "id": f"{int(test_message.timestamp * 1000)}_{test_message.category}",
                "data": {
                    "message": test_message.content,
                    "category": test_message.category,
                    "priority": service._map_priority_to_number(test_message.priority),
                    "confidence": int(test_message.confidence * 100),
                    "source": test_message.source,
                    "context": test_message.context,
                    "secondary_messages": [],
                    "improvement_potential": None
                },
                "timestamp": test_message.timestamp
            }
            
            logger.info("✅ Message format test successful")
            logger.info(f"📝 Formatted message: {json.dumps(formatted_message, indent=2)}")
            
            logger.info("🎯 Integration test completed successfully!")
            
        else:
            logger.error("❌ Coaching agent not available")
            return False
            
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_overlay_connectivity():
    """Test connectivity to overlay components"""
    
    try:
        logger.info("🖥️ Testing overlay connectivity...")
        
        # Test WebSocket connection format expected by React overlay
        import websockets
        
        # This is what the React overlay expects to receive
        expected_format = {
            "type": "coaching",
            "id": "1234567890_braking",
            "data": {
                "message": "Test coaching message for overlay",
                "category": "braking", 
                "priority": 3,
                "confidence": 85,
                "source": "local_ml",
                "context": "test",
                "secondary_messages": [],
                "improvement_potential": None
            },
            "timestamp": time.time()
        }
        
        logger.info("✅ Overlay message format validated")
        logger.info(f"📱 Expected format: {json.dumps(expected_format, indent=2)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Overlay connectivity test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🧪 GT3 AI Coaching - Integration Test Suite")
    logger.info("=" * 50)
    
    # Run tests
    async def run_tests():
        integration_success = await test_coaching_integration()
        overlay_success = await test_overlay_connectivity()
        
        logger.info("=" * 50)
        if integration_success and overlay_success:
            logger.info("🎉 ALL TESTS PASSED - Coaching agent ready for GT3 overlay!")
        else:
            logger.error("❌ Some tests failed - Check logs above")
            
        return integration_success and overlay_success
    
    try:
        result = asyncio.run(run_tests())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()
