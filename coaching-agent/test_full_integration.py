#!/usr/bin/env python3
"""
Full Integration Test - Segment Analysis with LLM
=================================================

Demonstrates the complete segment analysis pipeline with LLM integration.
"""

import asyncio
import logging
import time
from typing import Dict, Any

from track_metadata_manager import TrackMetadataManager
from segment_analyzer import SegmentAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class RealisticTelemetrySimulator:
    """Simulates realistic telemetry data for testing"""
    
    def __init__(self, track_name: str = "Silverstone"):
        self.track_name = track_name
        self.lap = 1
        self.lap_dist_pct = 0.0
        self.speed = 120.0
        self.throttle = 60.0
        self.brake = 0.0
        self.steering = 0.0
        self.rpm = 6000
        self.gear = 4
        
    def generate_telemetry(self) -> Dict[str, Any]:
        """Generate realistic telemetry data"""
        # Simulate lap progression
        self.lap_dist_pct += 0.005  # 0.5% per update (slower for realism)
        if self.lap_dist_pct >= 1.0:
            self.lap_dist_pct = 0.0
            self.lap += 1
            logger.info(f"🏁 Completed lap {self.lap - 1}")
        
        # Simulate realistic driving based on track position
        if 0.0 <= self.lap_dist_pct <= 0.05:  # Turn 1
            self.speed = max(80, self.speed - 2)
            self.throttle = 40
            self.brake = 30
            self.steering = 0.5
            self.gear = 3
        elif 0.05 <= self.lap_dist_pct <= 0.15:  # Straight
            self.speed = min(180, self.speed + 3)
            self.throttle = 95
            self.brake = 0
            self.steering = 0.0
            self.gear = 5
        elif 0.15 <= self.lap_dist_pct <= 0.25:  # Turn 2
            self.speed = max(70, self.speed - 3)
            self.throttle = 35
            self.brake = 50
            self.steering = 0.6
            self.gear = 3
        elif 0.25 <= self.lap_dist_pct <= 0.35:  # Straight
            self.speed = min(170, self.speed + 2)
            self.throttle = 90
            self.brake = 0
            self.steering = 0.0
            self.gear = 5
        elif 0.35 <= self.lap_dist_pct <= 0.45:  # Turn 3
            self.speed = max(75, self.speed - 2)
            self.throttle = 45
            self.brake = 40
            self.steering = 0.4
            self.gear = 3
        else:  # Other segments
            self.speed = max(90, min(160, self.speed + 1))
            self.throttle = 75
            self.brake = 10
            self.steering = 0.2
            self.gear = 4
        
        # Update RPM based on gear and speed
        self.rpm = min(8000, max(3000, self.speed * 50))
        
        return {
            'lap': self.lap,
            'lapDistPct': self.lap_dist_pct,
            'speed': self.speed,
            'throttle': self.throttle,
            'brake': self.brake,
            'steering': self.steering,
            'rpm': self.rpm,
            'gear': self.gear,
            'track_name': self.track_name,
            'timestamp': time.time()
        }

async def test_full_integration():
    """Test the complete segment analysis pipeline with LLM integration"""
    logger.info("🧪 Starting full integration test...")
    
    # Initialize components
    track_manager = TrackMetadataManager()
    segment_analyzer = SegmentAnalyzer(track_manager)
    
    # Test with a track that might need LLM generation
    track_name = "Silverstone"
    logger.info(f"🔍 Loading metadata for: {track_name}")
    
    # Get track metadata (will use LLM if not cached)
    segments = await track_manager.get_track_metadata(track_name)
    
    if not segments:
        logger.error(f"❌ No metadata available for {track_name}")
        return
    
    logger.info(f"✅ Loaded {len(segments)} segments for {track_name}")
    
    # Initialize segment analyzer
    segment_analyzer.update_track(track_name, segments)
    
    # Create telemetry simulator
    simulator = RealisticTelemetrySimulator(track_name)
    
    # Simulate driving for multiple laps
    lap_count = 0
    max_laps = 3
    
    logger.info("🚗 Starting realistic simulation...")
    
    while lap_count < max_laps:
        # Generate telemetry
        telemetry = simulator.generate_telemetry()
        
        # Buffer telemetry for analysis
        segment_analyzer.buffer_telemetry(telemetry)
        
        # Check if lap completed
        if telemetry['lap'] > lap_count:
            lap_count = telemetry['lap'] - 1
            logger.info(f"📊 Completed lap {lap_count}")
            
            # Show current segment
            current_segment = segment_analyzer.get_current_segment(telemetry['lapDistPct'])
            if current_segment:
                logger.info(f"📍 Current segment: {current_segment['name']} ({current_segment['type']})")
        
        # Small delay to simulate real-time
        await asyncio.sleep(0.05)  # 20Hz for realism
    
    logger.info("✅ Simulation complete!")
    
    # Show available tracks
    available_tracks = track_manager.get_available_tracks()
    logger.info(f"📁 Available tracks: {len(available_tracks)}")
    
    # Test with another track to demonstrate LLM generation
    logger.info("🔍 Testing LLM generation with new track...")
    new_track = "Mount Panorama"
    
    segments = await track_manager.get_track_metadata(new_track)
    if segments:
        logger.info(f"✅ Generated {len(segments)} segments for {new_track}")
        for i, segment in enumerate(segments[:3]):
            logger.info(f"   {i+1}. {segment['name']} ({segment['type']})")
    else:
        logger.warning(f"⚠️ No segments generated for {new_track}")

async def test_performance():
    """Test performance of the hybrid approach"""
    logger.info("⚡ Testing performance...")
    
    track_manager = TrackMetadataManager()
    
    # Test cache performance
    start_time = time.time()
    segments = await track_manager.get_track_metadata("Spa-Francorchamps")
    cache_time = time.time() - start_time
    
    logger.info(f"📁 Cache load time: {cache_time:.3f}s")
    
    # Test LLM performance (if available)
    start_time = time.time()
    segments = await track_manager.get_track_metadata("Fuji Speedway")
    llm_time = time.time() - start_time
    
    if segments:
        logger.info(f"🤖 LLM generation time: {llm_time:.3f}s")
    else:
        logger.info("🤖 LLM not available or failed")

async def main():
    """Main test function"""
    try:
        # Test performance first
        await test_performance()
        
        # Test full integration
        await test_full_integration()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 