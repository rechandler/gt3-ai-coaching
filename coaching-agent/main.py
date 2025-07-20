#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coaching Agent Startup Script
Initializes and starts the hybrid coaching agent
"""

import asyncio
import logging
import signal
import sys
import os
from typing import Dict, Any
import inspect

shutdown_event = None  # Global shutdown event for graceful shutdown

# Add the coaching-agent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hybrid_coach import HybridCoachingAgent
from config import ConfigManager, get_development_config, get_production_config
from coaching_data_service import CoachingDataService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('coaching_agent.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def maybe_await(result):
    if inspect.isawaitable(result):
        return await result
    return result

class CoachingAgentRunner:
    """Manages the coaching agent lifecycle"""
    
    def __init__(self, config_file: str = "", environment: str = 'development'):
        self.config_manager = ConfigManager(config_file)
        self.environment = environment
        self.agent = None
        self.running = False
        
        # Load environment-specific config
        if environment == 'production':
            env_config = get_production_config()
        else:
            env_config = get_development_config()
        
        # Merge with user config
        self.config_manager._merge_config(self.config_manager.config, env_config)
        
        # Validate configuration
        if not self.config_manager.validate_config():
            raise ValueError("Invalid configuration")
    
    async def start(self):
        """Start the coaching agent and the coaching data service"""
        try:
            logger.info("Starting GT3 Coaching Agent...")
            self.agent = HybridCoachingAgent(self.config_manager.get_config())
            self.running = True
            # Start the coaching data service
            self.coaching_data_service = CoachingDataService()
            logger.info("Starting Coaching Data Service...")
            await asyncio.gather(
                self.agent.start(),
                self.coaching_data_service.start_service()
            )
        except Exception as e:
            logger.error(f"Error starting coaching agent or data service: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the coaching agent"""
        if self.running and self.agent:
            logger.info("Stopping coaching agent...")
            try:
                result = self.agent.stop()
                print(f"About to await self.agent.stop(), got: {result} (type: {type(result)})")
                logger.debug(f"About to await self.agent.stop(), got: {result} (type: {type(result)})")
                if hasattr(result, '__await__'):
                    await result
                else:
                    logger.error(f"self.agent.stop() returned non-awaitable: {result} (type: {type(result)})")
                self.running = False
                logger.info("Coaching agent stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping coaching agent: {e}")
        return None
    
    async def process_telemetry(self, telemetry_data: Dict[str, Any]):
        """Process telemetry data through the agent"""
        if self.agent and self.running:
            await self.agent.process_telemetry(telemetry_data)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        if self.agent:
            return self.agent.get_stats()
        return {}

# Example telemetry data processor
class TelemetrySimulator:
    """Simulates telemetry data for testing"""
    
    def __init__(self):
        self.lap_progress = 0.0
        self.lap_count = 0
        self.speed = 100.0
        self.in_corner = False
    
    def generate_telemetry(self) -> Dict[str, Any]:
        """Generate simulated telemetry data"""
        # Simulate lap progression
        self.lap_progress += 0.01  # 1% per update
        if self.lap_progress >= 1.0:
            self.lap_progress = 0.0
            self.lap_count += 1
        
        # Simulate speed variation based on track position
        if 0.2 <= self.lap_progress <= 0.4:  # Corner section
            self.speed = max(60, self.speed - 2)
            self.in_corner = True
        else:  # Straight section
            self.speed = min(250, self.speed + 3)
            self.in_corner = False
        
        # Generate telemetry
        telemetry = {
            'timestamp': asyncio.get_event_loop().time(),
            'lap_distance_pct': self.lap_progress,
            'lap_count': self.lap_count,
            'speed': self.speed,
            'brake_pct': 80 if self.in_corner and self.speed > 100 else 0,
            'throttle_pct': 20 if self.in_corner else 85,
            'steering_angle': 0.3 if self.in_corner else 0.0,
            'gear': 3 if self.in_corner else 5,
            'rpm': 5000 if self.in_corner else 7000,
            'track_name': 'Test Track',
            'car_name': 'BMW M4 GT3',
            'session_type': 'practice'
        }
        
        # Simulate lap completion
        if self.lap_progress < 0.01 and self.lap_count > 0:
            telemetry['lap_completed'] = True
            telemetry['last_lap_time'] = 90.0 + (self.lap_count % 3) * 0.5  # Varying lap times
        
        return telemetry

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GT3 Coaching Agent')
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--environment', type=str, default='development', 
                       choices=['development', 'production'], help='Environment mode')
    parser.add_argument('--simulate', action='store_true', help='Run with simulated telemetry')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create and start the coaching agent
        runner = CoachingAgentRunner(args.config, args.environment)

        if args.simulate:
            # Run with simulated telemetry
            logger.info("Running in simulation mode...")
            simulator = TelemetrySimulator()

            # Start the agent in the background
            agent_task = asyncio.create_task(runner.start())

            # Wait a moment for startup
            await asyncio.sleep(2)

            # Send simulated telemetry
            while runner.running:
                telemetry = simulator.generate_telemetry()
                await runner.process_telemetry(telemetry)

                # Print stats occasionally
                if simulator.lap_count % 5 == 0 and simulator.lap_progress < 0.01:
                    stats = runner.get_stats()
                    logger.info(f"Agent stats: {stats}")

                await asyncio.sleep(0.1)  # 10Hz update rate

            await runner.stop()
            await agent_task

        else:
            # Run normally (waiting for real telemetry)
            logger.info("Waiting for telemetry data...")
            await runner.start()
            await runner.stop()

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user (KeyboardInterrupt)")
        await runner.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

    logger.info("Coaching agent shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
