#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reference Lap Manager
====================

Professional coaching requires comparing current performance against reference laps.
This module provides comprehensive reference lap management for:
- Personal best laps
- Engineer/reference laps  
- Optimal lap segments
- Delta time calculations
- Sector-by-sector comparisons

Features:
- Load and store reference lap data
- Segment-based performance analysis
- Delta time calculations
- Reference lap validation
- Multiple reference types (PB, engineer, optimal)
"""

import json
import os
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ReferenceLap:
    """Reference lap data structure"""
    track_name: str
    car_name: str
    lap_time: float
    lap_type: str  # 'personal_best', 'engineer', 'optimal', 'session_best'
    timestamp: float
    segments: Dict[str, 'ReferenceSegment'] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReferenceSegment:
    """Reference segment data"""
    segment_id: str
    segment_name: str
    start_pct: float
    end_pct: float
    segment_time: float
    entry_speed: float
    exit_speed: float
    min_speed: float
    max_speed: float
    avg_throttle: float
    avg_brake: float
    max_steering: float
    racing_line_score: float
    optimal_inputs: Dict[str, float] = field(default_factory=dict)

@dataclass
class DeltaAnalysis:
    """Delta time analysis results"""
    total_delta: float
    sector_deltas: Dict[str, float]
    segment_deltas: Dict[str, float]
    time_loss_locations: List[Tuple[str, float]]
    improvement_potential: float
    reference_type: str

class ReferenceManager:
    """Manages reference lap data and comparisons"""
    
    def __init__(self, data_dir: str = "reference_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Reference lap storage
        self.reference_laps: Dict[str, Dict[str, ReferenceLap]] = defaultdict(dict)
        self.current_track = ""
        self.current_car = ""
        
        # Performance tracking
        self.session_best_lap = None
        self.personal_best_lap = None
        self.engineer_reference_lap = None
        
        # Delta calculations
        self.current_lap_segments = {}
        self.current_lap_start_time = 0
        self.current_lap_time = 0
        
        logger.info("Reference Manager initialized")
    
    def load_reference_laps(self, track_name: str, car_name: str) -> bool:
        """Load reference laps for a track/car combination"""
        try:
            self.current_track = track_name
            self.current_car = car_name
            
            # Load from file
            file_path = self.data_dir / f"{track_name}_{car_name}_references.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct reference laps
                for lap_type, lap_data in data.items():
                    segments = {}
                    for seg_id, seg_data in lap_data.get('segments', {}).items():
                        segments[seg_id] = ReferenceSegment(**seg_data)
                    
                    self.reference_laps[track_name][lap_type] = ReferenceLap(
                        track_name=lap_data['track_name'],
                        car_name=lap_data['car_name'],
                        lap_time=lap_data['lap_time'],
                        lap_type=lap_data['lap_type'],
                        timestamp=lap_data['timestamp'],
                        segments=segments,
                        metadata=lap_data.get('metadata', {})
                    )
                
                logger.info(f"Loaded {len(self.reference_laps[track_name])} reference laps for {track_name}")
                return True
            else:
                logger.info(f"No reference data found for {track_name} {car_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading reference laps: {e}")
            return False
    
    def save_reference_lap(self, reference_lap: ReferenceLap) -> bool:
        """Save a reference lap to storage"""
        try:
            # Convert to serializable format
            lap_data = {
                'track_name': reference_lap.track_name,
                'car_name': reference_lap.car_name,
                'lap_time': reference_lap.lap_time,
                'lap_type': reference_lap.lap_type,
                'timestamp': reference_lap.timestamp,
                'segments': {},
                'metadata': reference_lap.metadata
            }
            
            # Convert segments
            for seg_id, segment in reference_lap.segments.items():
                lap_data['segments'][seg_id] = {
                    'segment_id': segment.segment_id,
                    'segment_name': segment.segment_name,
                    'start_pct': segment.start_pct,
                    'end_pct': segment.end_pct,
                    'segment_time': segment.segment_time,
                    'entry_speed': segment.entry_speed,
                    'exit_speed': segment.exit_speed,
                    'min_speed': segment.min_speed,
                    'max_speed': segment.max_speed,
                    'avg_throttle': segment.avg_throttle,
                    'avg_brake': segment.avg_brake,
                    'max_steering': segment.max_steering,
                    'racing_line_score': segment.racing_line_score,
                    'optimal_inputs': segment.optimal_inputs
                }
            
            # Load existing data
            file_path = self.data_dir / f"{reference_lap.track_name}_{reference_lap.car_name}_references.json"
            existing_data = {}
            if file_path.exists():
                with open(file_path, 'r') as f:
                    existing_data = json.load(f)
            
            # Add new reference lap
            existing_data[reference_lap.lap_type] = lap_data
            
            # Save back to file
            with open(file_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
            
            # Update in-memory storage
            self.reference_laps[reference_lap.track_name][reference_lap.lap_type] = reference_lap
            
            logger.info(f"Saved {reference_lap.lap_type} reference lap for {reference_lap.track_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving reference lap: {e}")
            return False
    
    def create_reference_from_telemetry(self, telemetry_data: List[Dict[str, Any]], 
                                      track_name: str, car_name: str, 
                                      lap_type: str = "personal_best") -> Optional[ReferenceLap]:
        """Create a reference lap from telemetry data"""
        if not telemetry_data:
            return None
        
        try:
            # Calculate lap time
            lap_time = telemetry_data[-1].get('lapCurrentLapTime', 0)
            if lap_time <= 0:
                return None
            
            # Segment the telemetry data
            segments = self._segment_telemetry_data(telemetry_data, track_name)
            
            # Create reference lap
            reference_lap = ReferenceLap(
                track_name=track_name,
                car_name=car_name,
                lap_time=lap_time,
                lap_type=lap_type,
                timestamp=time.time(),
                segments=segments,
                metadata={
                    'telemetry_points': len(telemetry_data),
                    'created_by': 'telemetry_analysis'
                }
            )
            
            return reference_lap
            
        except Exception as e:
            logger.error(f"Error creating reference lap: {e}")
            return None
    
    def _segment_telemetry_data(self, telemetry_data: List[Dict[str, Any]], 
                               track_name: str) -> Dict[str, ReferenceSegment]:
        """Segment telemetry data into track segments"""
        segments = {}
        
        # Get track segments (this would integrate with track metadata)
        track_segments = self._get_track_segments(track_name)
        
        for segment in track_segments:
            segment_id = segment['id']
            segment_name = segment['name']
            start_pct = segment['start_pct']
            end_pct = segment['end_pct']
            
            # Filter telemetry for this segment
            segment_telemetry = [
                t for t in telemetry_data 
                if start_pct <= t.get('lapDistPct', 0) < end_pct
            ]
            
            if not segment_telemetry:
                continue
            
                    # Calculate segment metrics
        speeds = [float(t.get('speed', 0)) for t in segment_telemetry]
        throttles = [float(t.get('throttle', 0)) for t in segment_telemetry]
        brakes = [float(t.get('brake', 0)) for t in segment_telemetry]
        steering = [float(abs(t.get('steering', 0))) for t in segment_telemetry]
        
        # Calculate segment time (rough estimate)
        segment_time = len(segment_telemetry) / 60  # Assuming 60Hz
        
        # Create reference segment
        segments[segment_id] = ReferenceSegment(
            segment_id=segment_id,
            segment_name=segment_name,
            start_pct=start_pct,
            end_pct=end_pct,
            segment_time=segment_time,
            entry_speed=speeds[0] if speeds else 0.0,
            exit_speed=speeds[-1] if speeds else 0.0,
            min_speed=min(speeds) if speeds else 0.0,
            max_speed=max(speeds) if speeds else 0.0,
            avg_throttle=sum(throttles) / len(throttles) if throttles else 0.0,
            avg_brake=sum(brakes) / len(brakes) if brakes else 0.0,
            max_steering=max(steering) if steering else 0.0,
            racing_line_score=self._calculate_racing_line_score(segment_telemetry),
            optimal_inputs=self._calculate_optimal_inputs(segment_telemetry)
        )
        
        return segments
    
    def _get_track_segments(self, track_name: str) -> List[Dict[str, Any]]:
        """Get track segments for a given track"""
        # This would integrate with track metadata manager
        # For now, return basic segments
        return [
            {'id': 's1', 'name': 'Sector 1', 'start_pct': 0.0, 'end_pct': 0.33},
            {'id': 's2', 'name': 'Sector 2', 'start_pct': 0.33, 'end_pct': 0.66},
            {'id': 's3', 'name': 'Sector 3', 'start_pct': 0.66, 'end_pct': 1.0}
        ]
    
    def _calculate_racing_line_score(self, telemetry: List[Dict[str, Any]]) -> float:
        """Calculate racing line score (0-1, higher is better)"""
        if len(telemetry) < 3:
            return 0.5
        
        # Calculate smoothness of inputs
        steering_changes = []
        throttle_changes = []
        
        for i in range(1, len(telemetry)):
            steering_diff = abs(float(telemetry[i].get('steering', 0)) - float(telemetry[i-1].get('steering', 0)))
            throttle_diff = abs(float(telemetry[i].get('throttle', 0)) - float(telemetry[i-1].get('throttle', 0)))
            
            steering_changes.append(steering_diff)
            throttle_changes.append(throttle_diff)
        
        # Lower variance = better score
        steering_variance = float(np.var(steering_changes)) if steering_changes else 0.0
        throttle_variance = float(np.var(throttle_changes)) if throttle_changes else 0.0
        
        # Convert to 0-1 score (lower variance = higher score)
        score = 1.0 / (1.0 + steering_variance + throttle_variance)
        return min(1.0, max(0.0, score))
    
    def _calculate_optimal_inputs(self, telemetry: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate optimal input values for the segment"""
        if not telemetry:
            return {}
        
        speeds = [float(t.get('speed', 0)) for t in telemetry]
        throttles = [float(t.get('throttle', 0)) for t in telemetry]
        brakes = [float(t.get('brake', 0)) for t in telemetry]
        
        return {
            'optimal_entry_speed': max(speeds) if speeds else 0.0,
            'optimal_exit_speed': max(speeds) if speeds else 0.0,
            'optimal_throttle_application': max(throttles) if throttles else 0.0,
            'optimal_brake_release': min(brakes) if brakes else 0.0
        }
    
    def calculate_delta_analysis(self, current_telemetry: Dict[str, Any], 
                               reference_type: str = "personal_best") -> Optional[DeltaAnalysis]:
        """Calculate delta analysis against reference lap"""
        if not self.current_track or reference_type not in self.reference_laps[self.current_track]:
            return None
        
        reference_lap = self.reference_laps[self.current_track][reference_type]
        current_lap_dist = current_telemetry.get('lapDistPct', 0)
        
        # Find current segment
        current_segment = None
        for segment in reference_lap.segments.values():
            if segment.start_pct <= current_lap_dist < segment.end_pct:
                current_segment = segment
                break
        
        if not current_segment:
            return None
        
        # Calculate deltas
        sector_deltas = {}
        segment_deltas = {}
        time_loss_locations = []
        
        # Calculate current segment time (simplified)
        current_segment_time = self._estimate_current_segment_time(current_telemetry)
        segment_delta = current_segment_time - current_segment.segment_time
        
        segment_deltas[current_segment.segment_id] = segment_delta
        
        if segment_delta > 0:
            time_loss_locations.append((current_segment.segment_name, segment_delta))
        
        # Calculate total delta (simplified)
        total_delta = sum(segment_deltas.values())
        
        # Calculate improvement potential
        improvement_potential = abs(total_delta) if total_delta < 0 else 0
        
        return DeltaAnalysis(
            total_delta=total_delta,
            sector_deltas=sector_deltas,
            segment_deltas=segment_deltas,
            time_loss_locations=time_loss_locations,
            improvement_potential=improvement_potential,
            reference_type=reference_type
        )
    
    def _estimate_current_segment_time(self, telemetry: Dict[str, Any]) -> float:
        """Estimate current segment time"""
        # Simplified calculation - would need more sophisticated tracking
        return 0.0
    
    def get_reference_context(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get reference context for coaching"""
        context = {
            'reference_available': False,
            'reference_type': None,
            'delta_to_reference': 0.0,
            'sector_deltas': {},
            'segment_deltas': {},
            'time_loss_locations': [],
            'improvement_potential': 0.0,
            'reference_speeds': {},
            'reference_inputs': {}
        }
        
        if not self.current_track or not self.reference_laps[self.current_track]:
            return context
        
        # Try different reference types in order of preference
        reference_types = ['personal_best', 'engineer', 'session_best']
        
        for ref_type in reference_types:
            if ref_type in self.reference_laps[self.current_track]:
                delta_analysis = self.calculate_delta_analysis(telemetry_data, ref_type)
                if delta_analysis:
                    context.update({
                        'reference_available': True,
                        'reference_type': ref_type,
                        'delta_to_reference': delta_analysis.total_delta,
                        'sector_deltas': delta_analysis.sector_deltas,
                        'segment_deltas': delta_analysis.segment_deltas,
                        'time_loss_locations': delta_analysis.time_loss_locations,
                        'improvement_potential': delta_analysis.improvement_potential
                    })
                    
                    # Add reference speeds and inputs for current segment
                    current_lap_dist = telemetry_data.get('lapDistPct', 0)
                    reference_lap = self.reference_laps[self.current_track][ref_type]
                    
                    for segment in reference_lap.segments.values():
                        if segment.start_pct <= current_lap_dist < segment.end_pct:
                            context['reference_speeds'] = {
                                'entry_speed': segment.entry_speed,
                                'exit_speed': segment.exit_speed,
                                'min_speed': segment.min_speed,
                                'max_speed': segment.max_speed
                            }
                            context['reference_inputs'] = segment.optimal_inputs
                            break
                    
                    break
        
        return context
    
    def update_session_best(self, lap_time: float, telemetry_data: List[Dict[str, Any]]):
        """Update session best lap"""
        if not self.session_best_lap or lap_time < self.session_best_lap.lap_time:
            reference_lap = self.create_reference_from_telemetry(
                telemetry_data, self.current_track, self.current_car, "session_best"
            )
            if reference_lap:
                self.session_best_lap = reference_lap
                self.save_reference_lap(reference_lap)
                logger.info(f"New session best lap: {lap_time:.3f}s")
    
    def get_available_references(self, track_name: str) -> List[str]:
        """Get available reference types for a track"""
        if track_name in self.reference_laps:
            return list(self.reference_laps[track_name].keys())
        return []
    
    def validate_reference_lap(self, reference_lap: ReferenceLap) -> bool:
        """Validate reference lap data"""
        if not reference_lap.track_name or not reference_lap.car_name:
            return False
        
        if reference_lap.lap_time <= 0:
            return False
        
        if not reference_lap.segments:
            return False
        
        # Check segment continuity
        sorted_segments = sorted(reference_lap.segments.values(), key=lambda x: x.start_pct)
        for i in range(len(sorted_segments) - 1):
            if abs(sorted_segments[i].end_pct - sorted_segments[i + 1].start_pct) > 0.01:
                return False
        
        return True 