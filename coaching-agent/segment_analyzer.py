"""
Segment Analyzer - Track Segment Performance Analysis
===================================================

Analyzes telemetry data by track segments and generates coaching feedback.
"""

import time
import logging
from typing import Dict, List, Any, Optional
from track_metadata_manager import TrackMetadataManager

logger = logging.getLogger(__name__)

class SegmentAnalyzer:
    def __init__(self, track_metadata_manager: TrackMetadataManager):
        self.track_metadata_manager = track_metadata_manager
        self.track_segments = []
        self.current_lap = None
        self.current_track = ""
        self.segment_buffers = []
        self.lap_history = {}  # Store previous laps for comparison
        self.best_lap_segments = {}  # Store best lap data per segment
        self.last_feedback_time = 0
        self.feedback_cooldown = 5.0  # Minimum seconds between feedback
        
    def update_track(self, track_name: str, segments: List[Dict]):
        """Update track segments when track changes"""
        self.current_track = track_name
        self.track_segments = segments
        self.segment_buffers = [[] for _ in self.track_segments]
        self.lap_history = {}
        self.best_lap_segments = {}
        logger.info(f"📍 Updated track segments for: {track_name} ({len(segments)} segments)")
        
    def buffer_telemetry(self, telemetry: Dict[str, Any]):
        """Buffer telemetry data by segment"""
        lap = telemetry.get('lap')
        lap_dist_pct = telemetry.get('lapDistPct')
        
        if lap is None or lap_dist_pct is None or not self.track_segments:
            return
            
        # New lap: analyze previous lap and reset buffers
        if self.current_lap is not None and lap != self.current_lap:
            self.analyze_lap(self.current_lap, self.segment_buffers)
            self.segment_buffers = [[] for _ in self.track_segments]
            
        self.current_lap = lap
        
        # Find current segment and buffer data
        for idx, segment in enumerate(self.track_segments):
            if segment['start_pct'] <= lap_dist_pct < segment['end_pct']:
                self.segment_buffers[idx].append(telemetry)
                break
                
    def analyze_lap(self, lap: int, segment_buffers: List[List[Dict]]) -> List[str]:
        """Analyze a completed lap and generate feedback"""
        logger.info(f"🏁 Analyzing lap {lap}...")
        
        lap_feedback = []
        lap_data = {}
        
        for idx, segment_data in enumerate(segment_buffers):
            if not segment_data:
                continue
                
            segment = self.track_segments[idx]
            segment_name = segment['name']
            
            # Analyze segment performance
            analysis = self.analyze_segment(segment, segment_data)
            
            if analysis['feedback']:
                lap_feedback.extend(analysis['feedback'])
                
            lap_data[segment_name] = analysis['metrics']
            
        # Store lap data for future comparison
        self.lap_history[lap] = lap_data
        
        # Update best lap if this lap was faster
        self.update_best_lap(lap, lap_data)
        
        return lap_feedback
        
    def analyze_segment(self, segment: Dict, segment_data: List[Dict]) -> Dict[str, Any]:
        """Analyze performance in a specific segment"""
        if not segment_data:
            return {'metrics': {}, 'feedback': []}
            
        # Calculate key metrics
        entry_speed = segment_data[0].get('speed', 0)
        exit_speed = segment_data[-1].get('speed', 0)
        min_speed = min(d.get('speed', 0) for d in segment_data)
        max_speed = max(d.get('speed', 0) for d in segment_data)
        
        avg_throttle = sum(d.get('throttle', 0) for d in segment_data) / len(segment_data)
        avg_brake = sum(d.get('brake', 0) for d in segment_data) / len(segment_data)
        max_steering = max(abs(d.get('steering', 0)) for d in segment_data)
        
        # Calculate segment time (rough estimate)
        segment_time = len(segment_data) / 60  # Assuming 60Hz telemetry
        
        # Calculate additional metrics
        speed_variance = max_speed - min_speed
        throttle_consistency = self.calculate_consistency([d.get('throttle', 0) for d in segment_data])
        brake_consistency = self.calculate_consistency([d.get('brake', 0) for d in segment_data])
        
        metrics = {
            'entry_speed': entry_speed,
            'exit_speed': exit_speed,
            'min_speed': min_speed,
            'max_speed': max_speed,
            'avg_throttle': avg_throttle,
            'avg_brake': avg_brake,
            'max_steering': max_steering,
            'segment_time': segment_time,
            'speed_variance': speed_variance,
            'throttle_consistency': throttle_consistency,
            'brake_consistency': brake_consistency
        }
        
        feedback = self.generate_segment_feedback(segment, metrics)
        
        return {'metrics': metrics, 'feedback': feedback}
        
    def calculate_consistency(self, values: List[float]) -> float:
        """Calculate consistency score (lower = more consistent)"""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5  # Standard deviation
        
    def generate_segment_feedback(self, segment: Dict, metrics: Dict) -> List[str]:
        """Generate feedback for a segment based on metrics"""
        feedback = []
        segment_name = segment['name']
        segment_type = segment['type']
        
        # Corner-specific feedback
        if segment_type == 'corner':
            if metrics['avg_throttle'] < 30:
                feedback.append(f"🚀 In {segment_name}: Apply throttle earlier for better exit speed")
            if metrics['avg_brake'] > 70:
                feedback.append(f"🛑 In {segment_name}: You're braking too hard, try a lighter touch")
            if metrics['max_steering'] > 0.8:
                feedback.append(f"🔄 In {segment_name}: Reduce steering input to avoid understeer")
            if metrics['exit_speed'] < metrics['entry_speed'] * 0.8:
                feedback.append(f"⚡ In {segment_name}: Focus on carrying more speed through the corner")
            if metrics['throttle_consistency'] > 20:
                feedback.append(f"📈 In {segment_name}: Be more consistent with throttle application")
                
        # Straight-specific feedback
        elif segment_type == 'straight':
            if metrics['avg_throttle'] < 90:
                feedback.append(f"🚀 In {segment_name}: Use full throttle on the straight")
            if metrics['max_speed'] < 150:
                feedback.append(f"🏎️ In {segment_name}: You can reach higher speeds here")
            if metrics['speed_variance'] > 20:
                feedback.append(f"📊 In {segment_name}: Maintain more consistent speed")
                
        # Chicane-specific feedback
        elif segment_type == 'chicane':
            if metrics['avg_throttle'] < 40:
                feedback.append(f"🚀 In {segment_name}: Apply throttle between the chicanes")
            if metrics['max_steering'] > 0.9:
                feedback.append(f"🔄 In {segment_name}: Smooth out your steering inputs")
                
        return feedback
        
    def update_best_lap(self, lap: int, lap_data: Dict):
        """Update best lap reference data"""
        # Simple implementation - could be more sophisticated
        if not self.best_lap_segments:
            self.best_lap_segments = lap_data
            logger.info(f"🥇 New best lap reference set: Lap {lap}")
        else:
            # Compare total lap time (rough estimate)
            current_total_time = sum(seg.get('segment_time', 0) for seg in lap_data.values())
            best_total_time = sum(seg.get('segment_time', 0) for seg in self.best_lap_segments.values())
            
            if current_total_time < best_total_time:
                self.best_lap_segments = lap_data
                logger.info(f"🥇 New best lap! Lap {lap} is faster")
                
    def get_current_segment(self, lap_dist_pct: float) -> Optional[Dict]:
        """Get the current segment based on lap distance percentage"""
        for segment in self.track_segments:
            if segment['start_pct'] <= lap_dist_pct < segment['end_pct']:
                return segment
        return None
        
    def should_send_feedback(self) -> bool:
        """Check if enough time has passed to send feedback"""
        current_time = time.time()
        if current_time - self.last_feedback_time >= self.feedback_cooldown:
            self.last_feedback_time = current_time
            return True
        return False 