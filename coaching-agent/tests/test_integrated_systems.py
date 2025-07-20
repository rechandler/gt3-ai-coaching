#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Integrated Systems
=======================

Tests all the integrated systems in the coaching agent to ensure they work together.
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any

# Add the coaching-agent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hybrid_coach import HybridCoachingAgent
from config import get_development_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_integrated_systems():
    """Test all integrated systems"""
    logger.info("Testing integrated coaching systems...")
    
    try:
        # Initialize coaching agent with development config
        config = get_development_config()
        agent = HybridCoachingAgent(config)
        
        # Start the agent
        await agent.start()
        logger.info("✅ Agent started successfully")
        
        # Generate test telemetry data
        test_telemetry = {
            'timestamp': asyncio.get_event_loop().time(),
            'lapDistPct': 0.25,  # 25% through lap
            'lap_count': 1,
            'speed': 120.0,
            'brake_pct': 60.0,
            'throttle_pct': 40.0,
            'steering_angle': 0.2,
            'gear': 3,
            'rpm': 6000,
            'track_name': 'Spa-Francorchamps',
            'car_name': 'BMW M4 GT3',
            'session_type': 'practice',
            'lapCurrentLapTime': 45.5,
            'lapBestLapTime': 44.2
        }
        
        # Process telemetry through all systems
        logger.info("Processing telemetry through all systems...")
        await agent.process_telemetry(test_telemetry)
        logger.info("✅ Telemetry processed successfully")
        
        # Test enhanced context builder
        logger.info("Testing enhanced context builder...")
        buffer_stats = agent.enhanced_context_builder.get_buffer_stats()
        logger.info(f"Enhanced context buffer stats: {buffer_stats}")
        
        # Test schema validator
        logger.info("Testing schema validator...")
        validation_result = agent.schema_validator.validate_telemetry(test_telemetry)
        logger.info(f"Schema validation result: {validation_result.is_valid}")
        
        # Test reference lap helper (if available)
        if agent.reference_lap_helper:
            logger.info("✅ Reference lap helper initialized")
        else:
            logger.info("⚠️ Reference lap helper not yet initialized (needs track info)")
        
        # Get insights from all systems
        logger.info("Getting insights from all systems...")
        insights = []
        
        # Get micro-analysis insights
        micro_insights = agent.get_micro_analysis_insights()
        if micro_insights:
            insights.extend(micro_insights)
            logger.info(f"✅ Micro-analysis insights: {len(micro_insights)}")
        
        # Get enhanced context insights
        enhanced_insights = agent.get_enhanced_context_insights(test_telemetry)
        if enhanced_insights:
            insights.extend(enhanced_insights)
            logger.info(f"✅ Enhanced context insights: {len(enhanced_insights)}")
        
        # Get persistent mistakes
        persistent_mistakes = agent.get_persistent_mistakes()
        logger.info(f"✅ Persistent mistakes: {len(persistent_mistakes)}")
        
        # Get session summary
        session_summary = agent.get_session_summary()
        logger.info(f"✅ Session summary generated")
        
        # Test stats
        stats = agent.get_stats()
        logger.info(f"✅ Agent stats: {stats}")
        
        # Stop the agent
        await agent.stop()
        logger.info("✅ Agent stopped successfully")
        
        # Summary
        logger.info("🎉 All integrated systems test completed successfully!")
        logger.info(f"Total insights generated: {len(insights)}")
        logger.info(f"Persistent mistakes tracked: {len(persistent_mistakes)}")
        logger.info(f"Schema validations: {agent.schema_validator.get_validation_stats()}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

async def test_session_api():
    """Test session API endpoints"""
    logger.info("Testing session API...")
    
    try:
        from session_api import SessionAPI
        
        # Initialize coaching agent
        config = get_development_config()
        agent = HybridCoachingAgent(config)
        await agent.start()
        
        # Initialize session API
        session_api = SessionAPI(agent)
        
        # Test API endpoints
        app = session_api.get_app()
        
        # Test health endpoint
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        response = client.get("/health")
        logger.info(f"Health endpoint response: {response.status_code}")
        
        response = client.get("/advice/session_summary")
        logger.info(f"Session summary endpoint response: {response.status_code}")
        
        response = client.get("/advice/persistent_mistakes")
        logger.info(f"Persistent mistakes endpoint response: {response.status_code}")
        
        await agent.stop()
        logger.info("✅ Session API test completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Session API test failed: {e}", exc_info=True)
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting integrated systems test...")
    
    # Test core systems
    core_success = await test_integrated_systems()
    
    # Test session API
    api_success = await test_session_api()
    
    if core_success and api_success:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 