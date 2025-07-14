#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Test: Telemetry Server + Coaching Agent
Tests the integration between the telemetry server and coaching agent
"""

import asyncio
import websockets
import json
import logging
import sys
import os
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelemetryCoachingIntegrationTest:
    """Test integration between telemetry server and coaching agent"""
    
    def __init__(self):
        self.coaching_messages_received = []
        self.telemetry_messages_received = []
        self.connection_confirmed = False
        
    async def test_coaching_integration(self):
        """Test the full integration"""
        logger.info("🧪 Starting Telemetry + Coaching Integration Test")
        
        try:
            # Connect to the coaching data service UI interface
            uri = "ws://localhost:8082"
            async with websockets.connect(uri) as websocket:
                logger.info(f"✅ Connected to coaching data service at {uri}")
                
                # Send initial status request
                await websocket.send(json.dumps({
                    "type": "getStatus"
                }))
                
                # Listen for messages for a period of time
                timeout_time = time.time() + 30  # Test for 30 seconds
                
                while time.time() < timeout_time:
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        await self.handle_test_message(message)
                        
                    except asyncio.TimeoutError:
                        # No message received, continue
                        pass
                
                # Summarize test results
                await self.summarize_test_results()
                
        except ConnectionRefusedError:
            logger.error("❌ Could not connect to coaching data service")
            logger.error("   Make sure the telemetry server is running:")
            logger.error("   cd telemetry-server && python services/launcher.py")
            return False
        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}")
            return False
    
    async def handle_test_message(self, message: str):
        """Handle messages received during test"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            if message_type == "connected":
                self.connection_confirmed = True
                logger.info("✅ Connection to coaching data service confirmed")
            
            elif message_type == "status":
                status_data = data.get("data", {})
                logger.info("📊 Service Status:")
                logger.info(f"   Telemetry Connected: {status_data.get('telemetryConnected', False)}")
                logger.info(f"   Session Connected: {status_data.get('sessionConnected', False)}")
                logger.info(f"   Current Track: {status_data.get('currentTrack', 'Unknown')}")
                logger.info(f"   Current Car: {status_data.get('currentCar', 'Unknown')}")
                
                # Check coaching agent status
                coaching_info = status_data.get('coachingAgent', {})
                logger.info(f"🧠 Coaching Agent:")
                logger.info(f"   Available: {coaching_info.get('available', False)}")
                logger.info(f"   Active: {coaching_info.get('active', False)}")
                
                if coaching_info.get('stats'):
                    stats = coaching_info['stats']
                    logger.info(f"   Total Messages: {stats.get('total_messages', 0)}")
                    logger.info(f"   AI Usage Rate: {stats.get('ai_usage_rate', 0)}")
            
            elif message_type == "telemetry":
                self.telemetry_messages_received.append(data)
                telemetry_data = data.get("data", {})
                
                # Log basic telemetry info
                speed = telemetry_data.get('speed', 0)
                if len(self.telemetry_messages_received) % 20 == 1:  # Log every 20th message
                    logger.info(f"📊 Telemetry: Speed={speed:.1f} km/h")
                    
                    # Check for coaching stats in telemetry
                    if 'coaching_stats' in telemetry_data:
                        logger.info("🧠 Coaching stats present in telemetry data")
            
            elif message_type == "coaching_message":
                self.coaching_messages_received.append(data)
                coaching_data = data.get("data", {})
                
                logger.info("🧠 COACHING MESSAGE RECEIVED:")
                logger.info(f"   Content: {coaching_data.get('content', 'No content')}")
                logger.info(f"   Category: {coaching_data.get('category', 'Unknown')}")
                logger.info(f"   Priority: {coaching_data.get('priority', 'Unknown')}")
                logger.info(f"   Source: {coaching_data.get('source', 'Unknown')}")
                logger.info(f"   Confidence: {coaching_data.get('confidence', 0):.2f}")
            
            elif message_type == "sessionInfo":
                session_data = data.get("data", {})
                logger.info(f"🏁 Session Info: Track={session_data.get('track_name', 'Unknown')}")
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"Error handling test message: {e}")
    
    async def summarize_test_results(self):
        """Summarize the test results"""
        logger.info("=" * 60)
        logger.info("🧪 INTEGRATION TEST RESULTS")
        logger.info("=" * 60)
        
        logger.info(f"✅ Connection Established: {self.connection_confirmed}")
        logger.info(f"📊 Telemetry Messages Received: {len(self.telemetry_messages_received)}")
        logger.info(f"🧠 Coaching Messages Received: {len(self.coaching_messages_received)}")
        
        # Evaluate success
        success = True
        
        if not self.connection_confirmed:
            logger.error("❌ Connection was not confirmed")
            success = False
        
        if len(self.telemetry_messages_received) == 0:
            logger.warning("⚠️ No telemetry messages received (iRacing may not be running)")
            logger.info("   This is expected if iRacing is not active")
        else:
            logger.info("✅ Telemetry data flow confirmed")
        
        if len(self.coaching_messages_received) == 0:
            logger.info("ℹ️ No coaching messages received")
            logger.info("   This is normal if no coaching triggers occurred during test")
        else:
            logger.info("✅ Coaching message flow confirmed")
            for i, msg in enumerate(self.coaching_messages_received):
                coaching_data = msg.get("data", {})
                logger.info(f"   {i+1}. [{coaching_data.get('category')}] {coaching_data.get('content')}")
        
        if success:
            logger.info("🎉 INTEGRATION TEST PASSED")
        else:
            logger.error("❌ INTEGRATION TEST FAILED")
        
        logger.info("=" * 60)
        
        return success

async def main():
    """Main test function"""
    test = TelemetryCoachingIntegrationTest()
    
    logger.info("Starting integration test in 3 seconds...")
    logger.info("Make sure the telemetry server is running!")
    await asyncio.sleep(3)
    
    success = await test.test_coaching_integration()
    
    if success:
        logger.info("✅ Integration test completed successfully")
    else:
        logger.error("❌ Integration test failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
