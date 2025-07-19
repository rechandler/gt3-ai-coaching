#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lap Buffer Manager
==================

Comprehensive lap and sector buffering system for accurate "best lap," 
"rolling stint," and "compare to pro" functionality.

Features:
- Real-time lap/sector telemetry buffering
- Automatic lap completion detection
- Sector time calculation and tracking
- Personal best lap management
- Reference lap persistence (per car/track)
- Rolling stint analysis
- Professional comparison data
"""

import json
import os
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class LapData:
    """Complete lap telemetry data"""
    lap_number: int
    lap_time: float
    sector_times: List[float]
    telemetry_points: List[Dict[str, Any]]
    track_name: str
    car_name: str
    timestamp: float
    is_valid: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SectorData:
    """Sector telemetry and timing data"""
    sector_number: int
    sector_time: float
    telemetry_points: List[Dict[str, Any]]
    entry_speed: float
    exit_speed: float
    min_speed: float
    max_speed: float
    avg_throttle: float
    avg_brake: float
    max_steering: float
    start_pct: float
    end_pct: float

@dataclass
class ReferenceLap:
    """Reference lap for comparison"""
    lap_data: LapData
    reference_type: str  # 'personal_best', 'session_best', 'engineer', 'optimal'
    created_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class LapBufferManager:
    """Manages real-time lap and sector buffering with reference tracking"""
    
    def __init__(self, data_dir: str = "lap_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Current lap buffering
        self.current_lap_buffer: List[Dict[str, Any]] = []
        self.current_lap_start_time: Optional[float] = None
        self.current_lap_number: Optional[int] = None
        self.current_sector_buffers: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        
        # Lap history
        self.completed_laps: List[LapData] = []
        self.session_best_lap: Optional[LapData] = None
        self.personal_best_lap: Optional[LapData] = None
        
        # Sector tracking
        self.sector_boundaries: List[float] = [0.0, 0.33, 0.66, 1.0]  # Default 3 sectors
        self.current_sector: int = 0
        self.sector_start_time: Optional[float] = None
        self.sector_times: List[float] = []
        
        # Reference laps
        self.reference_laps: Dict[str, ReferenceLap] = {}
        self.current_track: str = ""
        self.current_car: str = ""
        
        # Performance tracking
        self.best_sector_times: List[float] = [float('inf')] * 3
        self.session_sector_bests: List[float] = [float('inf')] * 3
        
        # Rolling stint analysis
        self.stint_laps: List[LapData] = []
        self.stint_start_time: Optional[float] = None
        
        logger.info("Lap Buffer Manager initialized")
    
    def update_track_info(self, track_name: str, car_name: str, sector_boundaries: Optional[List[float]] = None):
        """Update track and car information"""
        if track_name != self.current_track or car_name != self.current_car:
            self.current_track = track_name
            self.current_car = car_name
            self.load_reference_laps()
            logger.info(f"🔄 Updated track: {track_name}, car: {car_name}")
        
        if sector_boundaries:
            self.sector_boundaries = sector_boundaries
            logger.info(f"📏 Updated sector boundaries: {sector_boundaries}")
    
    def buffer_telemetry(self, telemetry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Buffer telemetry data and detect lap/sector changes"""
        try:
            # Extract key telemetry fields
            lap_number = telemetry.get('lap')
            lap_dist_pct = telemetry.get('lapDistPct', 0.0)
            current_time = time.time()
            
            # Check for new lap
            if lap_number is not None and lap_number != self.current_lap_number:
                if self.current_lap_number is not None:
                    # Complete previous lap
                    completed_lap = self.complete_current_lap(telemetry)
                    if completed_lap:
                        self.completed_laps.append(completed_lap)
                        self.update_best_laps(completed_lap)
                        self.update_stint_analysis(completed_lap)
                        
                        return {
                            'type': 'lap_completed',
                            'lap_data': completed_lap,
                            'is_personal_best': completed_lap.lap_time < (self.personal_best_lap.lap_time if self.personal_best_lap else float('inf')),
                            'is_session_best': completed_lap.lap_time < (self.session_best_lap.lap_time if self.session_best_lap else float('inf'))
                        }
                
                # Start new lap
                self.start_new_lap(lap_number, current_time)
            
            # Check for sector change
            sector_change = self.check_sector_change(lap_dist_pct, current_time)
            if sector_change:
                return sector_change
            
            # Buffer current telemetry
            self.current_lap_buffer.append(telemetry.copy())
            
            # Buffer to current sector
            if self.current_sector < len(self.sector_boundaries) - 1:
                self.current_sector_buffers[self.current_sector].append(telemetry.copy())
            
            return None
            
        except Exception as e:
            logger.error(f"Error buffering telemetry: {e}")
            return None
    
    def start_new_lap(self, lap_number: int, start_time: float):
        """Start buffering a new lap"""
        self.current_lap_number = lap_number
        self.current_lap_start_time = start_time
        self.current_lap_buffer = []
        self.current_sector_buffers = defaultdict(list)
        self.current_sector = 0
        self.sector_start_time = start_time
        self.sector_times = []
        
        logger.debug(f"🏁 Started buffering lap {lap_number}")
    
    def check_sector_change(self, lap_dist_pct: float, current_time: float) -> Optional[Dict[str, Any]]:
        """Check if we've moved to a new sector"""
        # Determine current sector
        new_sector = 0
        for i, boundary in enumerate(self.sector_boundaries[1:], 1):
            if lap_dist_pct < boundary:
                new_sector = i - 1
                break
        else:
            new_sector = len(self.sector_boundaries) - 2
        
        # Check for sector change
        if new_sector != self.current_sector:
            # Complete previous sector
            if self.sector_start_time is not None:
                sector_time = current_time - self.sector_start_time
                self.sector_times.append(sector_time)
                
                # Create sector data
                sector_data = self.create_sector_data(
                    self.current_sector,
                    sector_time,
                    self.current_sector_buffers[self.current_sector]
                )
                
                # Update best sector times
                if sector_time < self.best_sector_times[self.current_sector]:
                    self.best_sector_times[self.current_sector] = sector_time
                
                if sector_time < self.session_sector_bests[self.current_sector]:
                    self.session_sector_bests[self.current_sector] = sector_time
                
                # Update for next sector
                self.current_sector = new_sector
                self.sector_start_time = current_time
                
                return {
                    'type': 'sector_completed',
                    'sector_data': sector_data,
                    'is_best_sector': sector_time < self.best_sector_times[self.current_sector],
                    'is_session_best_sector': sector_time < self.session_sector_bests[self.current_sector]
                }
        
        return None
    
    def complete_current_lap(self, final_telemetry: Dict[str, Any]) -> Optional[LapData]:
        """Complete the current lap and create lap data"""
        if not self.current_lap_buffer or self.current_lap_start_time is None:
            return None
        
        try:
            # Calculate lap time
            lap_time = final_telemetry.get('lapLastLapTime', 0)
            if lap_time <= 0:
                # Estimate lap time from telemetry
                lap_time = time.time() - self.current_lap_start_time
            
            # Complete final sector if needed
            if self.sector_start_time is not None:
                final_sector_time = time.time() - self.sector_start_time
                self.sector_times.append(final_sector_time)
            
            # Ensure we have 3 sector times
            while len(self.sector_times) < 3:
                self.sector_times.append(0.0)
            
            # Create lap data
            lap_data = LapData(
                lap_number=self.current_lap_number or 0,
                lap_time=lap_time,
                sector_times=self.sector_times[:3],
                telemetry_points=self.current_lap_buffer.copy(),
                track_name=self.current_track,
                car_name=self.current_car,
                timestamp=time.time(),
                metadata={
                    'sector_boundaries': self.sector_boundaries,
                    'telemetry_count': len(self.current_lap_buffer)
                }
            )
            
            logger.info(f"🏁 Completed lap {self.current_lap_number}: {lap_time:.3f}s")
            return lap_data
            
        except Exception as e:
            logger.error(f"Error completing lap: {e}")
            return None
    
    def create_sector_data(self, sector_number: int, sector_time: float, 
                          telemetry_points: List[Dict[str, Any]]) -> SectorData:
        """Create sector data from telemetry points"""
        if not telemetry_points:
            return SectorData(
                sector_number=sector_number,
                sector_time=sector_time,
                telemetry_points=[],
                entry_speed=0.0,
                exit_speed=0.0,
                min_speed=0.0,
                max_speed=0.0,
                avg_throttle=0.0,
                avg_brake=0.0,
                max_steering=0.0,
                start_pct=self.sector_boundaries[sector_number],
                end_pct=self.sector_boundaries[sector_number + 1]
            )
        
        # Calculate sector metrics
        speeds = [t.get('speed', 0) for t in telemetry_points]
        throttles = [t.get('throttle', 0) for t in telemetry_points]
        brakes = [t.get('brake', 0) for t in telemetry_points]
        steerings = [abs(t.get('steering', 0)) for t in telemetry_points]
        
        return SectorData(
            sector_number=sector_number,
            sector_time=sector_time,
            telemetry_points=telemetry_points,
            entry_speed=speeds[0] if speeds else 0.0,
            exit_speed=speeds[-1] if speeds else 0.0,
            min_speed=min(speeds) if speeds else 0.0,
            max_speed=max(speeds) if speeds else 0.0,
            avg_throttle=float(np.mean(throttles)) if throttles else 0.0,
            avg_brake=float(np.mean(brakes)) if brakes else 0.0,
            max_steering=max(steerings) if steerings else 0.0,
            start_pct=self.sector_boundaries[sector_number],
            end_pct=self.sector_boundaries[sector_number + 1]
        )
    
    def update_best_laps(self, lap_data: LapData):
        """Update best lap references"""
        # Update session best
        if not self.session_best_lap or lap_data.lap_time < self.session_best_lap.lap_time:
            self.session_best_lap = lap_data
            logger.info(f"🥇 New session best lap: {lap_data.lap_time:.3f}s")
        
        # Update personal best
        if not self.personal_best_lap or lap_data.lap_time < self.personal_best_lap.lap_time:
            self.personal_best_lap = lap_data
            self.save_reference_lap(lap_data, 'personal_best')
            logger.info(f"🏆 New personal best lap: {lap_data.lap_time:.3f}s")
    
    def update_stint_analysis(self, lap_data: LapData):
        """Update rolling stint analysis"""
        if self.stint_start_time is None:
            self.stint_start_time = time.time()
        
        self.stint_laps.append(lap_data)
        
        # Keep only last 20 laps for rolling analysis
        if len(self.stint_laps) > 20:
            self.stint_laps = self.stint_laps[-20:]
    
    def get_rolling_stint_analysis(self) -> Dict[str, Any]:
        """Get rolling stint performance analysis"""
        if len(self.stint_laps) < 3:
            return {}
        
        lap_times = [lap.lap_time for lap in self.stint_laps]
        recent_laps = lap_times[-5:] if len(lap_times) >= 5 else lap_times
        
        analysis = {
            'total_laps': len(self.stint_laps),
            'stint_duration': time.time() - (self.stint_start_time or time.time()),
            'avg_lap_time': np.mean(lap_times),
            'best_lap_time': min(lap_times),
            'worst_lap_time': max(lap_times),
            'lap_time_consistency': np.std(lap_times),
            'recent_avg': np.mean(recent_laps),
            'trend': 'improving' if len(recent_laps) >= 3 and recent_laps[-1] < recent_laps[0] else 'stable',
            'consistency_score': 1.0 - (np.std(lap_times) / np.mean(lap_times)) if np.mean(lap_times) > 0 else 0.0
        }
        
        return analysis
    
    def get_current_lap_progress(self) -> Dict[str, Any]:
        """Get current lap progress and timing"""
        if not self.current_lap_buffer or self.current_lap_start_time is None:
            return {}
        
        current_time = time.time()
        elapsed_time = current_time - self.current_lap_start_time
        
        # Calculate sector progress
        current_sector_progress = 0.0
        if self.sector_times:
            current_sector_progress = sum(self.sector_times) / elapsed_time if elapsed_time > 0 else 0.0
        
        return {
            'lap_number': self.current_lap_number,
            'elapsed_time': elapsed_time,
            'current_sector': self.current_sector,
            'sector_times': self.sector_times.copy(),
            'telemetry_points': len(self.current_lap_buffer),
            'sector_progress': current_sector_progress
        }
    
    def get_reference_comparison(self, reference_type: str = 'personal_best') -> Optional[Dict[str, Any]]:
        """Get comparison data against reference lap"""
        reference_lap = self.reference_laps.get(reference_type)
        if not reference_lap:
            return None
        
        ref_lap_data = reference_lap.lap_data
        current_progress = self.get_current_lap_progress()
        
        if not current_progress:
            return None
        
        # Calculate delta to reference
        elapsed_time = current_progress['elapsed_time']
        delta_to_reference = elapsed_time - ref_lap_data.lap_time
        
        # Calculate sector deltas
        sector_deltas = []
        for i, current_sector_time in enumerate(current_progress['sector_times']):
            if i < len(ref_lap_data.sector_times):
                sector_delta = current_sector_time - ref_lap_data.sector_times[i]
                sector_deltas.append(sector_delta)
            else:
                sector_deltas.append(0.0)
        
        return {
            'reference_type': reference_type,
            'reference_lap_time': ref_lap_data.lap_time,
            'current_elapsed': elapsed_time,
            'delta_to_reference': delta_to_reference,
            'sector_deltas': sector_deltas,
            'is_ahead': delta_to_reference < 0,
            'reference_lap_data': ref_lap_data
        }
    
    def save_reference_lap(self, lap_data: LapData, reference_type: str):
        """Save a reference lap for future comparison"""
        try:
            reference_lap = ReferenceLap(
                lap_data=lap_data,
                reference_type=reference_type,
                created_at=time.time(),
                metadata={
                    'track_name': lap_data.track_name,
                    'car_name': lap_data.car_name,
                    'sector_boundaries': lap_data.metadata.get('sector_boundaries', [])
                }
            )
            
            self.reference_laps[reference_type] = reference_lap
            
            # Save to file
            self.save_reference_laps_to_file()
            
            logger.info(f"💾 Saved {reference_type} reference lap: {lap_data.lap_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Error saving reference lap: {e}")
    
    def load_reference_laps(self):
        """Load reference laps from file"""
        try:
            file_path = self.data_dir / f"{self.current_track}_{self.current_car}_references.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                for ref_type, ref_data in data.items():
                    # Reconstruct lap data
                    lap_data = LapData(**ref_data['lap_data'])
                    reference_lap = ReferenceLap(
                        lap_data=lap_data,
                        reference_type=ref_type,
                        created_at=ref_data['created_at'],
                        metadata=ref_data.get('metadata', {})
                    )
                    self.reference_laps[ref_type] = reference_lap
                
                logger.info(f"📁 Loaded {len(self.reference_laps)} reference laps")
                
        except Exception as e:
            logger.error(f"Error loading reference laps: {e}")
    
    def save_reference_laps_to_file(self):
        """Save reference laps to file"""
        try:
            file_path = self.data_dir / f"{self.current_track}_{self.current_car}_references.json"
            
            data = {}
            for ref_type, reference_lap in self.reference_laps.items():
                data[ref_type] = {
                    'lap_data': {
                        'lap_number': reference_lap.lap_data.lap_number,
                        'lap_time': reference_lap.lap_data.lap_time,
                        'sector_times': reference_lap.lap_data.sector_times,
                        'track_name': reference_lap.lap_data.track_name,
                        'car_name': reference_lap.lap_data.car_name,
                        'timestamp': reference_lap.lap_data.timestamp,
                        'is_valid': reference_lap.lap_data.is_valid,
                        'metadata': reference_lap.lap_data.metadata
                    },
                    'created_at': reference_lap.created_at,
                    'metadata': reference_lap.metadata
                }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving reference laps to file: {e}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary"""
        if not self.completed_laps:
            return {}
        
        lap_times = [lap.lap_time for lap in self.completed_laps]
        stint_analysis = self.get_rolling_stint_analysis()
        
        summary = {
            'total_laps': len(self.completed_laps),
            'session_best_lap': self.session_best_lap.lap_time if self.session_best_lap else None,
            'personal_best_lap': self.personal_best_lap.lap_time if self.personal_best_lap else None,
            'avg_lap_time': np.mean(lap_times),
            'lap_time_consistency': np.std(lap_times),
            'best_sector_times': self.best_sector_times,
            'session_sector_bests': self.session_sector_bests,
            'stint_analysis': stint_analysis,
            'track_name': self.current_track,
            'car_name': self.current_car
        }
        
        return summary 