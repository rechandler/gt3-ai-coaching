#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Lap Buffer System
======================

Comprehensive test script demonstrating the lap buffer system functionality:
- Real-time lap/sector telemetry buffering
- Automatic lap completion detection
- Sector time calculation and tracking
- Personal best lap management
- Reference lap persistence (per car/track)
- Rolling stint analysis
- Professional comparison data
"""

import asyncio
import time
import logging
from typing import Dict, List, Any
from lap_buffer_manager import LapBufferManager
from reference_lap_helper import ReferenceLapHelper, create_reference_lap_helper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelemetrySimulator:
    """Simulates realistic telemetry data for testing"""
    
    def __init__(self, track_name: str = "Spa-Francorchamps", car_name: str = "BMW M4 GT3"):
        self.track_name = track_name
        self.car_name = car_name
        self.lap_number = 1
        self.lap_progress = 0.0
        self.sector_times = [0.0, 0.0, 0.0]
        self.sector_progress = 0.0
        self.current_sector = 0
        self.sector_boundaries = [0.0, 0.33, 0.66, 1.0]
        
        # Simulate realistic lap times
        self.base_lap_time = 90.0  # 90 seconds base lap
        self.lap_variation = 2.0   # ±2 seconds variation
        self.sector_variations = [0.5, 0.8, 0.7]  # Sector-specific variations
        
    def generate_telemetry(self) -> Dict[str, Any]:
        """Generate realistic telemetry data"""
        # Simulate lap progression
        self.lap_progress += 0.01  # 1% per update
        
        # Check for lap completion
        if self.lap_progress >= 1.0:
            self.lap_progress = 0.0
            self.lap_number += 1
            self.sector_progress = 0.0
            self.current_sector = 0
        
        # Check for sector change
        for i, boundary in enumerate(self.sector_boundaries[1:], 1):
            if self.lap_progress < boundary:
                if self.current_sector != i - 1:
                    self.current_sector = i - 1
                    self.sector_progress = 0.0
                break
        
        # Calculate realistic speeds based on track position
        if 0.0 <= self.lap_progress < 0.05:  # La Source
            speed = 80 + (self.lap_progress * 400)  # Accelerating out
        elif 0.05 <= self.lap_progress < 0.15:  # Eau Rouge + Kemmel
            speed = 120 + (self.lap_progress * 200)
        elif 0.15 <= self.lap_progress < 0.25:  # Les Combes
            speed = 100 + (self.lap_progress * 150)
        elif 0.25 <= self.lap_progress < 0.35:  # Pouhon
            speed = 140 + (self.lap_progress * 100)
        elif 0.35 <= self.lap_progress < 0.45:  # Stavelot
            speed = 130 + (self.lap_progress * 120)
        elif 0.45 <= self.lap_progress < 0.55:  # Blanchimont
            speed = 150 + (self.lap_progress * 80)
        elif 0.55 <= self.lap_progress < 0.65:  # Bus Stop
            speed = 90 + (self.lap_progress * 100)
        else:  # Final straight
            speed = 160 + (self.lap_progress * 60)
        
        # Generate telemetry
        telemetry = {
            'timestamp': time.time(),
            'lap': self.lap_number,
            'lapDistPct': self.lap_progress,
            'speed': speed,
            'throttle': 85 if speed > 100 else 40,
            'brake': 20 if 0.05 <= self.lap_progress <= 0.15 else 0,
            'steering': 0.1 if 0.05 <= self.lap_progress <= 0.15 else 0.0,
            'gear': 5 if speed > 120 else 3,
            'rpm': 7000 if speed > 150 else 5000,
            'track_name': self.track_name,
            'car_name': self.car_name,
            'session_type': 'practice'
        }
        
        # Simulate lap completion
        if self.lap_progress < 0.01 and self.lap_number > 1:
            telemetry['lapCompleted'] = True
            telemetry['lapLastLapTime'] = self.base_lap_time + (self.lap_number % 3) * 0.5
        
        return telemetry

async def test_lap_buffer_system():
    """Test the complete lap buffer system"""
    logger.info("🧪 Starting lap buffer system test...")
    
    # Initialize components
    lap_buffer_manager = LapBufferManager()
    reference_helper = create_reference_lap_helper(lap_buffer_manager)
    simulator = TelemetrySimulator()
    
    # Set up track info
    lap_buffer_manager.update_track_info(
        simulator.track_name,
        simulator.car_name,
        simulator.sector_boundaries
    )
    
    # Track events for analysis
    events = []
    
    def on_lap_event(event_type: str, data: Any):
        events.append({
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        })
        logger.info(f"📊 Event: {event_type}")
    
    # Register callback
    reference_helper.register_reference_update_callback(on_lap_event)
    
    # Simulate 10 laps
    logger.info("🏁 Simulating 10 laps...")
    
    for lap in range(10):
        logger.info(f"Starting lap {lap + 1}")
        
        # Simulate lap telemetry
        for _ in range(100):  # 100 telemetry points per lap
            telemetry = simulator.generate_telemetry()
            
            # Buffer telemetry
            lap_event = lap_buffer_manager.buffer_telemetry(telemetry)
            
            if lap_event:
                event_type = lap_event.get('type')
                if event_type == 'lap_completed':
                    lap_data = lap_event.get('lap_data')
                    if lap_data:
                        # Check for reference updates
                        updates = reference_helper.check_and_update_reference_laps(lap_data)
                        
                        logger.info(f"Lap {lap_data.lap_number} completed: {lap_data.lap_time:.3f}s")
                        if updates['personal_best_updated']:
                            logger.info("🏆 NEW PERSONAL BEST!")
                        if updates['sector_bests_updated']:
                            logger.info(f"📊 Sector bests: {updates['sector_bests_updated']}")
                
                elif event_type == 'sector_completed':
                    sector_data = lap_event.get('sector_data')
                    if sector_data:
                        logger.info(f"Sector {sector_data.sector_number + 1}: {sector_data.sector_time:.3f}s")
            
            await asyncio.sleep(0.01)  # 10ms between telemetry points
    
    # Analyze results
    logger.info("\n📈 Test Results:")
    logger.info("=" * 50)
    
    # Session summary
    session_summary = reference_helper.get_session_summary()
    logger.info(f"Total laps: {session_summary.get('total_laps', 0)}")
    logger.info(f"Session best: {session_summary.get('session_best_lap', 'N/A')}")
    logger.info(f"Personal best: {session_summary.get('personal_best_lap', 'N/A')}")
    logger.info(f"Average lap time: {session_summary.get('avg_lap_time', 0):.3f}s")
    
    # Rolling stint analysis
    stint_analysis = reference_helper.get_rolling_stint_analysis()
    if stint_analysis:
        logger.info(f"Stint analysis: {stint_analysis.get('total_laps', 0)} laps")
        logger.info(f"Consistency score: {stint_analysis.get('consistency_score', 0):.2f}")
        logger.info(f"Trend: {stint_analysis.get('trend', 'unknown')}")
    
    # Reference comparison
    comparison = reference_helper.get_reference_comparison_summary('personal_best')
    if comparison:
        logger.info(f"Reference comparison: {comparison.get('delta_to_reference', 0):.3f}s")
    
    # Available references
    available_refs = session_summary.get('reference_laps', {}).get('available_references', [])
    logger.info(f"Available references: {available_refs}")
    
    logger.info("✅ Lap buffer system test completed!")

async def test_reference_persistence():
    """Test reference lap persistence across sessions"""
    logger.info("\n💾 Testing reference lap persistence...")
    
    # Create buffer manager
    lap_buffer_manager = LapBufferManager()
    
    # Simulate first session
    simulator = TelemetrySimulator("Monza", "Ferrari 488 GT3")
    lap_buffer_manager.update_track_info(simulator.track_name, simulator.car_name)
    
    # Complete a few laps
    for lap in range(3):
        for _ in range(100):
            telemetry = simulator.generate_telemetry()
            lap_event = lap_buffer_manager.buffer_telemetry(telemetry)
            if lap_event and lap_event.get('type') == 'lap_completed':
                lap_data = lap_event.get('lap_data')
                if lap_data:
                    lap_buffer_manager.update_best_laps(lap_data)
            await asyncio.sleep(0.01)
    
    # Check if references were saved
    logger.info(f"Personal best saved: {lap_buffer_manager.personal_best_lap is not None}")
    logger.info(f"Session best saved: {lap_buffer_manager.session_best_lap is not None}")
    
    # Create new buffer manager (simulating new session)
    new_lap_buffer_manager = LapBufferManager()
    new_lap_buffer_manager.update_track_info(simulator.track_name, simulator.car_name)
    
    # Check if references were loaded
    logger.info(f"References loaded: {len(new_lap_buffer_manager.reference_laps)}")
    
    logger.info("✅ Reference persistence test completed!")

async def test_sector_analysis():
    """Test sector-by-sector analysis"""
    logger.info("\n📊 Testing sector analysis...")
    
    lap_buffer_manager = LapBufferManager()
    simulator = TelemetrySimulator("Nürburgring Grand Prix", "Porsche 911 GT3 R")
    
    # Custom sector boundaries for Nürburgring
    sector_boundaries = [0.0, 0.25, 0.50, 0.75, 1.0]  # 4 sectors
    lap_buffer_manager.update_track_info(simulator.track_name, simulator.car_name, sector_boundaries)
    
    sector_events = []
    
    # Simulate one lap with detailed sector tracking
    for _ in range(200):  # More telemetry points for detailed analysis
        telemetry = simulator.generate_telemetry()
        lap_event = lap_buffer_manager.buffer_telemetry(telemetry)
        
        if lap_event and lap_event.get('type') == 'sector_completed':
            sector_data = lap_event.get('sector_data')
            if sector_data:
                sector_events.append({
                    'sector': sector_data.sector_number + 1,
                    'time': sector_data.sector_time,
                    'entry_speed': sector_data.entry_speed,
                    'exit_speed': sector_data.exit_speed,
                    'avg_throttle': sector_data.avg_throttle,
                    'avg_brake': sector_data.avg_brake
                })
        
        await asyncio.sleep(0.005)  # 5ms for more detailed simulation
    
    # Analyze sector performance
    logger.info("Sector Analysis:")
    for event in sector_events:
        logger.info(f"Sector {event['sector']}: {event['time']:.3f}s "
                   f"(Entry: {event['entry_speed']:.0f}km/h, "
                   f"Exit: {event['exit_speed']:.0f}km/h)")
    
    logger.info("✅ Sector analysis test completed!")

async def main():
    """Run all tests"""
    logger.info("🚀 Starting comprehensive lap buffer system tests...")
    
    try:
        # Test basic lap buffer functionality
        await test_lap_buffer_system()
        
        # Test reference persistence
        await test_reference_persistence()
        
        # Test sector analysis
        await test_sector_analysis()
        
        logger.info("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 