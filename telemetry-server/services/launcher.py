"""
Service Launcher for GT3 AI Coaching Platform
============================================

This script starts all the modular services for the GT3 AI coaching platform:

1. Telemetry Service (ports 9001, 9002)
   - Connects to iRacing SDK
   - Streams telemetry data (9001) 
   - Streams session/driver data (9002)

2. Coaching Data Service (port 8082)  
   - Receives data from telemetry service
   - Processes data for coaching insights
   - Serves processed data to UI

Architecture:
iRacing SDK → Telemetry Service → Coaching Data Service → React UI

This replaces the monolithic telemetry-server.py with focused, modular services.
"""

import asyncio
import logging
import signal
import sys
import time
from typing import List
import multiprocessing

# Import our services
from .telemetry_service import TelemetryService
from .coaching_data_service import CoachingDataService

logger = logging.getLogger(__name__)

class ServiceLauncher:
    """Manages launching and coordinating multiple services"""
    
    def __init__(self):
        self.services = []
        self.running = True
        
    async def start_telemetry_service(self):
        """Start the telemetry service"""
        try:
            logger.info("🚀 Starting Telemetry Service...")
            service = TelemetryService(
                host="localhost",
                telemetry_port=9001,
                session_port=9002
            )
            await service.start_servers()
        except Exception as e:
            logger.error(f"❌ Telemetry service failed: {e}")
            raise
    
    async def start_coaching_data_service(self):
        """Start the coaching data service"""
        try:
            # Wait a moment for telemetry service to start
            await asyncio.sleep(2)
            
            logger.info("🚀 Starting Coaching Data Service...")
            service = CoachingDataService(
                telemetry_host="localhost",
                telemetry_port=9001,
                session_port=9002,
                ui_host="localhost",
                ui_port=8082
            )
            await service.start_service()
        except Exception as e:
            logger.error(f"❌ Coaching data service failed: {e}")
            raise
    
    async def start_all_services(self):
        """Start all services concurrently"""
        logger.info("🚀 Starting GT3 AI Coaching Platform Services")
        logger.info("=" * 60)
        logger.info("Architecture:")
        logger.info("  iRacing SDK → Telemetry Service → Coaching Data Service → React UI")
        logger.info("")
        
        # Check for coaching agent availability
        import os
        coaching_agent_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'coaching-agent')
        coaching_available = os.path.exists(os.path.join(coaching_agent_path, 'hybrid_coach.py'))
        
        logger.info("Services:")
        logger.info("  📊 Telemetry Service:     ws://localhost:9001 (telemetry), ws://localhost:9002 (session)")
        logger.info("  📈 Coaching Data Service: ws://localhost:8082 (UI interface)")
        if coaching_available:
            logger.info("  🧠 AI Coaching Agent:     Integrated with Coaching Data Service")
        else:
            logger.info("  ⚠️  AI Coaching Agent:     NOT AVAILABLE (running without AI coaching)")
        logger.info("=" * 60)
        
        try:
            # Start both services concurrently
            await asyncio.gather(
                self.start_telemetry_service(),
                self.start_coaching_data_service()
            )
        except Exception as e:
            logger.error(f"❌ Service startup failed: {e}")
            raise
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown on signals"""
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, shutting down services...")
            self.running = False
            # Let the event loop handle the shutdown
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

def run_in_process(coro):
    """Run an async coroutine in a separate process"""
    try:
        # Setup logging for this process
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Run the coroutine
        asyncio.run(coro)
    except KeyboardInterrupt:
        logger.info("🏁 Service process stopped by user")
    except Exception as e:
        logger.error(f"❌ Service process failed: {e}")

def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🏁 GT3 AI Coaching Platform - Service Launcher")
    
    # Option 1: Run services in same process (easier for development)
    launcher = ServiceLauncher()
    launcher.setup_signal_handlers()
    
    try:
        asyncio.run(launcher.start_all_services())
    except KeyboardInterrupt:
        logger.info("🏁 All services stopped by user")
    except Exception as e:
        logger.error(f"❌ Service launcher failed: {e}")
        sys.exit(1)

def main_multiprocess():
    """Alternative main that runs services in separate processes"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🏁 GT3 AI Coaching Platform - Multi-Process Service Launcher")
    
    # Create service processes
    processes = []
    
    try:
        # Start telemetry service process
        telemetry_service = TelemetryService()
        p1 = multiprocessing.Process(
            target=run_in_process, 
            args=(telemetry_service.start_servers(),),
            name="TelemetryService"
        )
        p1.start()
        processes.append(p1)
        logger.info("📊 Started Telemetry Service process")
        
        # Wait a moment before starting coaching service
        time.sleep(2)
        
        # Start coaching data service process  
        coaching_service = CoachingDataService()
        p2 = multiprocessing.Process(
            target=run_in_process,
            args=(coaching_service.start_service(),),
            name="CoachingDataService"
        )
        p2.start()
        processes.append(p2)
        logger.info("📈 Started Coaching Data Service process")
        
        # Wait for all processes
        for p in processes:
            p.join()
            
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down all service processes...")
        for p in processes:
            p.terminate()
            p.join()
        logger.info("🏁 All services stopped")
    except Exception as e:
        logger.error(f"❌ Multi-process launcher failed: {e}")
        for p in processes:
            p.terminate()
            p.join()
        sys.exit(1)

if __name__ == "__main__":
    # Use single-process mode by default for easier development
    main()
    
    # Uncomment this line to use multi-process mode instead:
    # main_multiprocess()
