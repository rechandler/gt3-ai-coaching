#!/usr/bin/env python3
"""
Test Script for Segment Analysis
================================

Demonstrates the segment-based telemetry analysis and feedback generation.
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

class TelemetrySimulator:
    """Simulates telemetry data for testing segment analysis"""
    
    def __init__(self, track_name: str = "Spa-Francorchamps"):
        self.track_name = track_name
        self.lap = 1
        self.lap_dist_pct = 0.0
        self.speed = 100.0
        self.throttle = 50.0
        self.brake = 0.0
        self.steering = 0.0
        self.segment_progress = 0.0
        
    def generate_telemetry(self) -> Dict[str, Any]:
        """Generate simulated telemetry data"""
        # Simulate lap progression
        self.lap_dist_pct += 0.01  # 1% per update
        if self.lap_dist_pct >= 1.0:
            self.lap_dist_pct = 0.0
            self.lap += 1
            logger.info(f"🏁 Completed lap {self.lap - 1}")
        
        # Simulate different driving conditions based on track position
        if 0.03 <= self.lap_dist_pct <= 0.08:  # Eau Rouge
            self.speed = max(80, self.speed - 3)
            self.throttle = 30
            self.brake = 20
            self.steering = 0.6
        elif 0.08 <= self.lap_dist_pct <= 0.15:  # Kemmel Straight
            self.speed = min(200, self.speed + 5)
            self.throttle = 95
            self.brake = 0
            self.steering = 0.0
        elif 0.15 <= self.lap_dist_pct <= 0.22:  # Les Combes
            self.speed = max(60, self.speed - 4)
            self.throttle = 40
            self.brake = 60
            self.steering = 0.4
        else:  # Other segments
            self.speed = max(90, min(180, self.speed + 1))
            self.throttle = 70
            self.brake = 10
            self.steering = 0.2
        
        return {
            'lap': self.lap,
            'lapDistPct': self.lap_dist_pct,
            'speed': self.speed,
            'throttle': self.throttle,
            'brake': self.brake,
            'steering': self.steering,
            'track_name': self.track_name,
            'timestamp': time.time()
        }

async def test_segment_analysis():
    """Test the segment analysis functionality"""
    logger.info("🧪 Starting segment analysis test...")
    
    # Initialize components
    track_manager = TrackMetadataManager()
    segment_analyzer = SegmentAnalyzer(track_manager)
    
    # Load track metadata
    track_name = "Spa-Francorchamps"
    segments = await track_manager.get_track_metadata(track_name)
    
    if not segments:
        logger.error(f"❌ No metadata available for {track_name}")
        return
    
    logger.info(f"✅ Loaded {len(segments)} segments for {track_name}")
    
    # Initialize segment analyzer
    segment_analyzer.update_track(track_name, segments)
    
    # Create telemetry simulator
    simulator = TelemetrySimulator(track_name)
    
    # Simulate driving for a few laps
    lap_count = 0
    max_laps = 3
    
    logger.info("🚗 Starting simulation...")
    
    while lap_count < max_laps:
        # Generate telemetry
        telemetry = simulator.generate_telemetry()
        
        # Buffer telemetry for analysis
        segment_analyzer.buffer_telemetry(telemetry)
        
        # Check if lap completed
        if telemetry['lap'] > lap_count:
            lap_count = telemetry['lap'] - 1
            logger.info(f"📊 Completed lap {lap_count}")
        
        # Small delay to simulate real-time
        await asyncio.sleep(0.1)
    
    logger.info("✅ Simulation complete!")
    
    # Show available tracks
    available_tracks = track_manager.get_available_tracks()
    logger.info(f"📁 Available tracks: {available_tracks}")

async def main():
    """Main test function"""
    try:
        await test_segment_analysis()
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 