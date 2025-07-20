#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telemetry Analyzer
Processes and analyzes incoming telemetry data for coaching insights
"""

import numpy as np
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
import math

logger = logging.getLogger(__name__)

@dataclass
class LapAnalysis:
    """Analysis results for a lap"""
    lap_number: int
    lap_time: float
    sector_times: List[float]
    max_speed: float
    avg_speed: float
    brake_events: int
    throttle_usage: float
    consistency_score: float
    racing_line_deviation: float

@dataclass
class CornerAnalysis:
    """Analysis for a specific corner"""
    corner_id: str
    entry_speed: float
    apex_speed: float
    exit_speed: float
    braking_point: float
    throttle_point: float
    racing_line_score: float
    time_loss: float

class MotionCalculator:
    """Calculates motion-related metrics from telemetry"""
    
    def __init__(self):
        self.previous_data = None
        self.dt = 0.1  # Assume 10Hz data
    
    def calculate_acceleration(self, current_speed: float, previous_speed: float, 
                             dt: float = None) -> float:
        """Calculate acceleration from speed difference"""
        if dt is None:
            dt = self.dt
        
        if dt <= 0:
            return 0.0
        
        return (current_speed - previous_speed) / dt
    
    def calculate_g_forces(self, telemetry: Dict[str, Any], 
                          previous_telemetry: Dict[str, Any] = None) -> Dict[str, float]:
        """Calculate G-forces from telemetry data"""
        g_forces = {'longitudinal': 0.0, 'lateral': 0.0, 'total': 0.0}
        
        if not previous_telemetry:
            return g_forces
        
        # Longitudinal G (acceleration/braking)
        speed_diff = telemetry.get('speed', 0) - previous_telemetry.get('speed', 0)
        accel_ms2 = speed_diff * 0.277778 / self.dt  # km/h to m/s conversion
        g_forces['longitudinal'] = accel_ms2 / 9.81
        
        # Lateral G (cornering) - simplified calculation
        speed_ms = telemetry.get('speed', 0) * 0.277778  # km/h to m/s
        steering_angle = telemetry.get('steering_angle', 0)
        
        if speed_ms > 0 and abs(steering_angle) > 0.01:
            # Rough approximation of lateral G
            g_forces['lateral'] = (speed_ms ** 2 * abs(steering_angle)) / (9.81 * 50)  # Assuming 50m radius
        
        # Total G
        g_forces['total'] = math.sqrt(g_forces['longitudinal']**2 + g_forces['lateral']**2)
        
        return g_forces

class SectorAnalyzer:
    """Analyzes sector performance"""
    
    def __init__(self):
        self.sector_boundaries = [0.0, 0.33, 0.66, 1.0]  # Default sector splits
        self.sector_data = defaultdict(list)
        self.current_sector = 0
        self.sector_start_time = 0
    
    def update_sector_boundaries(self, boundaries: List[float]):
        """Update sector boundaries for specific track"""
        self.sector_boundaries = boundaries
    
    def analyze_sector(self, telemetry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze current sector performance"""
        lap_distance = telemetry.get('lap_distance_pct', 0.0)
        current_time = time.time()
        
        # Determine current sector
        new_sector = 0
        for i, boundary in enumerate(self.sector_boundaries[1:], 1):
            if lap_distance < boundary:
                new_sector = i - 1
                break
        else:
            new_sector = len(self.sector_boundaries) - 2
        
        # Check for sector change
        if new_sector != self.current_sector:
            # Calculate sector time
            sector_time = current_time - self.sector_start_time
            
            analysis = {
                'sector': self.current_sector,
                'sector_time': sector_time,
                'avg_speed': self.calculate_sector_avg_speed(),
                'max_speed': self.calculate_sector_max_speed(),
                'improvements': self.identify_improvements()
            }
            
            # Store sector data
            self.sector_data[self.current_sector].append({
                'time': sector_time,
                'timestamp': current_time,
                'telemetry': telemetry.copy()
            })
            
            # Update for next sector
            self.current_sector = new_sector
            self.sector_start_time = current_time
            
            return analysis
        
        return None
    
    def calculate_sector_avg_speed(self) -> float:
        """Calculate average speed for current sector"""
        # Placeholder - would need to track speed throughout sector
        return 0.0
    
    def calculate_sector_max_speed(self) -> float:
        """Calculate maximum speed for current sector"""
        # Placeholder - would need to track speed throughout sector
        return 0.0
    
    def identify_improvements(self) -> List[str]:
        """Identify potential improvements for the sector"""
        improvements = []
        
        if self.current_sector == 0:  # First sector
            improvements.extend(['braking_optimization', 'racing_line'])
        elif self.current_sector == 1:  # Middle sector
            improvements.extend(['cornering_technique', 'throttle_control'])
        else:  # Final sector
            improvements.extend(['corner_exit', 'straight_line_speed'])
        
        return improvements

class CornerDetector:
    """Detects and analyzes corners"""
    
    def __init__(self):
        self.steering_threshold = 0.1  # 10% steering input to detect corner
        self.corners = {}
        self.current_corner = None
        self.corner_start_position = 0
    
    def detect_corner(self, telemetry: Dict[str, Any]) -> Optional[CornerAnalysis]:
        """Detect and analyze corners"""
        steering_angle = abs(telemetry.get('steering_angle', 0))
        lap_position = telemetry.get('lap_distance_pct', 0)
        speed = telemetry.get('speed', 0)
        
        # Corner entry detection
        if steering_angle > self.steering_threshold and self.current_corner is None:
            self.current_corner = {
                'start_position': lap_position,
                'start_speed': speed,
                'max_steering': steering_angle,
                'min_speed': speed,
                'braking_detected': telemetry.get('brake_pct', 0) > 10,
                'telemetry_data': [telemetry.copy()]
            }
        
        # Corner progression
        elif self.current_corner is not None:
            self.current_corner['telemetry_data'].append(telemetry.copy())
            self.current_corner['max_steering'] = max(
                self.current_corner['max_steering'], steering_angle
            )
            self.current_corner['min_speed'] = min(
                self.current_corner['min_speed'], speed
            )
            
            # Corner exit detection
            if steering_angle < self.steering_threshold * 0.5:
                return self.finalize_corner_analysis(telemetry)
        
        return None
    
    def finalize_corner_analysis(self, exit_telemetry: Dict[str, Any]) -> CornerAnalysis:
        """Finalize corner analysis"""
        if not self.current_corner:
            return None
        
        corner_data = self.current_corner
        corner_id = f"corner_{corner_data['start_position']:.2f}"
        
        # Calculate corner metrics
        entry_speed = corner_data['start_speed']
        apex_speed = corner_data['min_speed']
        exit_speed = exit_telemetry.get('speed', 0)
        
        # Analyze racing line (simplified)
        racing_line_score = self.calculate_racing_line_score(corner_data['telemetry_data'])
        
        # Calculate time loss (simplified)
        time_loss = self.estimate_time_loss(corner_data)
        
        analysis = CornerAnalysis(
            corner_id=corner_id,
            entry_speed=entry_speed,
            apex_speed=apex_speed,
            exit_speed=exit_speed,
            braking_point=corner_data['start_position'],
            throttle_point=self.find_throttle_point(corner_data['telemetry_data']),
            racing_line_score=racing_line_score,
            time_loss=time_loss
        )
        
        # Reset for next corner
        self.current_corner = None
        
        return analysis
    
    def calculate_racing_line_score(self, telemetry_data: List[Dict[str, Any]]) -> float:
        """Calculate racing line score (0-1, higher is better)"""
        # Simplified scoring based on smoothness
        if len(telemetry_data) < 3:
            return 0.5
        
        steering_changes = 0
        for i in range(1, len(telemetry_data)):
            steering_diff = abs(
                telemetry_data[i].get('steering_angle', 0) - 
                telemetry_data[i-1].get('steering_angle', 0)
            )
            if steering_diff > 0.05:  # 5% steering change
                steering_changes += 1
        
        # Fewer steering changes = better line
        smoothness = max(0, 1 - (steering_changes / len(telemetry_data)))
        return smoothness
    
    def find_throttle_point(self, telemetry_data: List[Dict[str, Any]]) -> float:
        """Find where throttle was first applied in corner"""
        for data in telemetry_data:
            if data.get('throttle_pct', 0) > 10:  # 10% throttle
                return data.get('lap_distance_pct', 0)
        
        return 0.0
    
    def estimate_time_loss(self, corner_data: Dict[str, Any]) -> float:
        """Estimate time loss in corner (simplified)"""
        # This would be more sophisticated in a real implementation
        return 0.0

class TelemetryAnalyzer:
    """Main telemetry analysis engine"""
    
    def __init__(self):
        self.motion_calculator = MotionCalculator()
        self.sector_analyzer = SectorAnalyzer()
        self.corner_detector = CornerDetector()
        
        # State tracking
        self.previous_telemetry = None
        self.lap_start_time = 0
        self.current_lap_data = []
        self.completed_laps = []
        
        # Performance tracking
        self.best_lap_time = float('inf')
        self.best_sector_times = [float('inf')] * 3
        
        # Gear advisory state
        self.gear_too_high_start = None
        self.gear_too_low_start = None
        self.gear_advisory_active = None
        
        logger.info("Telemetry Analyzer initialized")
    
    def analyze(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main analysis function"""
        analysis = {
            'timestamp': time.time(),
            'motion': {},
            'sector': None,
            'corner': None,
            'lap': None,
            'performance': {},
            'gear_advisory': None
        }
        
        try:
            now = time.time()
            # Calculate motion metrics
            if self.previous_telemetry:
                analysis['motion'] = self.motion_calculator.calculate_g_forces(
                    telemetry_data, self.previous_telemetry
                )
            
            # Analyze sectors
            sector_analysis = self.sector_analyzer.analyze_sector(telemetry_data)
            if sector_analysis:
                analysis['sector'] = sector_analysis
            
            # Detect corners
            corner_analysis = self.corner_detector.detect_corner(telemetry_data)
            if corner_analysis:
                analysis['corner'] = corner_analysis
            
            # Track lap data
            self.current_lap_data.append(telemetry_data.copy())
            
            # Check for lap completion
            if telemetry_data.get('lap_completed', False):
                lap_analysis = self.analyze_completed_lap(telemetry_data)
                if lap_analysis:
                    analysis['lap'] = lap_analysis
            
            # Calculate performance metrics
            analysis['performance'] = self.calculate_performance_metrics(telemetry_data)

            # --- Gear too high/low detection ---
            rpm = telemetry_data.get('rpm', 0)
            throttle = telemetry_data.get('throttle_pct', 0)
            speed = telemetry_data.get('speed', 0)
            gear = telemetry_data.get('gear', 0)
            advisory = None
            threshold_duration = 2.0  # seconds
            # Too high gear: low RPM, high throttle, moderate speed
            if rpm > 0 and throttle > 40 and speed > 40 and rpm < 2000 and gear > 1:
                if self.gear_too_high_start is None:
                    self.gear_too_high_start = now
                elif now - self.gear_too_high_start > threshold_duration:
                    advisory = {
                        'type': 'gear_too_high',
                        'message': 'Consider downshifting: RPM is low for current speed and throttle.'
                    }
                    self.gear_advisory_active = 'high'
            else:
                self.gear_too_high_start = None
                if self.gear_advisory_active == 'high':
                    self.gear_advisory_active = None
            # Too low gear: high RPM, low speed
            if rpm > 7000 and speed < 60 and gear > 1:
                if self.gear_too_low_start is None:
                    self.gear_too_low_start = now
                elif now - self.gear_too_low_start > threshold_duration:
                    advisory = {
                        'type': 'gear_too_low',
                        'message': 'Consider upshifting: RPM is high for current speed.'
                    }
                    self.gear_advisory_active = 'low'
            else:
                self.gear_too_low_start = None
                if self.gear_advisory_active == 'low':
                    self.gear_advisory_active = None
            if advisory:
                analysis['gear_advisory'] = advisory
            # --- End gear too high/low detection ---

            # Update state
            self.previous_telemetry = telemetry_data.copy()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in telemetry analysis: {e}")
            return analysis
    
    def analyze_completed_lap(self, telemetry_data: Dict[str, Any]) -> Optional[LapAnalysis]:
        """Analyze a completed lap"""
        if not self.current_lap_data:
            return None
        
        try:
            lap_time = telemetry_data.get('last_lap_time', 0)
            if lap_time <= 0:
                return None
            
            # Calculate lap metrics
            speeds = [data.get('speed', 0) for data in self.current_lap_data]
            max_speed = max(speeds) if speeds else 0
            avg_speed = np.mean(speeds) if speeds else 0
            
            # Count brake events
            brake_events = 0
            for i, data in enumerate(self.current_lap_data):
                if (data.get('brake_pct', 0) > 10 and 
                    i > 0 and self.current_lap_data[i-1].get('brake_pct', 0) <= 10):
                    brake_events += 1
            
            # Calculate throttle usage
            throttle_values = [data.get('throttle_pct', 0) for data in self.current_lap_data]
            throttle_usage = np.mean(throttle_values) if throttle_values else 0
            
            # Calculate consistency score (simplified)
            consistency_score = self.calculate_consistency_score()
            
            # Create lap analysis
            lap_analysis = LapAnalysis(
                lap_number=len(self.completed_laps) + 1,
                lap_time=lap_time,
                sector_times=telemetry_data.get('sector_times', [0, 0, 0]),
                max_speed=max_speed,
                avg_speed=avg_speed,
                brake_events=brake_events,
                throttle_usage=throttle_usage,
                consistency_score=consistency_score,
                racing_line_deviation=0.0  # Placeholder
            )
            
            # Store completed lap
            self.completed_laps.append(lap_analysis)
            
            # Update bests
            if lap_time < self.best_lap_time:
                self.best_lap_time = lap_time
            
            # Reset for next lap
            self.current_lap_data = []
            
            return lap_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing completed lap: {e}")
            return None
    
    def calculate_consistency_score(self) -> float:
        """Calculate consistency score for recent laps"""
        if len(self.completed_laps) < 3:
            return 1.0
        
        recent_times = [lap.lap_time for lap in self.completed_laps[-5:]]
        if not recent_times:
            return 1.0
        
        variation = np.std(recent_times) / np.mean(recent_times)
        consistency = max(0, 1 - variation * 10)  # Scale variation
        
        return consistency
    
    def calculate_performance_metrics(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate current performance metrics"""
        metrics = {
            'speed_efficiency': 0.0,
            'brake_efficiency': 0.0,
            'throttle_efficiency': 0.0,
            'racing_line_efficiency': 0.0
        }
        
        # Speed efficiency (current speed vs theoretical max for position)
        current_speed = telemetry_data.get('speed', 0)
        theoretical_max = self.get_theoretical_max_speed(
            telemetry_data.get('lap_distance_pct', 0)
        )
        if theoretical_max > 0:
            metrics['speed_efficiency'] = min(1.0, current_speed / theoretical_max)
        
        # Brake efficiency (using optimal brake pressure)
        brake_pct = telemetry_data.get('brake_pct', 0)
        if brake_pct > 0:
            # Simplified: efficiency based on brake pressure vs speed
            optimal_brake = min(100, current_speed * 0.8)  # Simple heuristic
            if optimal_brake > 0:
                metrics['brake_efficiency'] = min(1.0, brake_pct / optimal_brake)
        
        # Throttle efficiency
        throttle_pct = telemetry_data.get('throttle_pct', 0)
        steering_angle = abs(telemetry_data.get('steering_angle', 0))
        
        # Less throttle should be used when steering more
        if steering_angle > 0.1:  # In a corner
            optimal_throttle = max(0, 100 - steering_angle * 200)
            if optimal_throttle > 0:
                metrics['throttle_efficiency'] = 1.0 - abs(throttle_pct - optimal_throttle) / 100
        else:  # On straight
            metrics['throttle_efficiency'] = throttle_pct / 100
        
        return metrics
    
    def get_theoretical_max_speed(self, lap_position: float) -> float:
        """Get theoretical maximum speed for track position"""
        # Simplified speed map - would be track-specific in real implementation
        if 0.0 <= lap_position < 0.2:  # Start straight
            return 250
        elif 0.2 <= lap_position < 0.4:  # First sector
            return 120
        elif 0.4 <= lap_position < 0.6:  # Second sector
            return 180
        elif 0.6 <= lap_position < 0.8:  # Third sector
            return 150
        else:  # Final sector
            return 220
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of analysis results"""
        return {
            'total_laps': len(self.completed_laps),
            'best_lap_time': self.best_lap_time if self.best_lap_time != float('inf') else 0,
            'best_sector_times': self.best_sector_times,
            'avg_lap_time': (
                np.mean([lap.lap_time for lap in self.completed_laps]) 
                if self.completed_laps else 0
            ),
            'consistency_trend': self.get_consistency_trend(),
            'performance_trend': self.get_performance_trend()
        }
    
    def get_consistency_trend(self) -> str:
        """Get consistency trend description"""
        if len(self.completed_laps) < 3:
            return "insufficient_data"
        
        recent_consistency = np.mean([
            lap.consistency_score for lap in self.completed_laps[-3:]
        ])
        
        if recent_consistency > 0.8:
            return "improving"
        elif recent_consistency > 0.6:
            return "stable"
        else:
            return "inconsistent"
    
    def get_performance_trend(self) -> str:
        """Get performance trend description"""
        if len(self.completed_laps) < 3:
            return "insufficient_data"
        
        recent_times = [lap.lap_time for lap in self.completed_laps[-3:]]
        if len(recent_times) >= 2:
            if recent_times[-1] < recent_times[0]:
                return "improving"
            elif recent_times[-1] > recent_times[0] * 1.02:  # 2% slower
                return "declining"
            else:
                return "stable"
        
        return "unknown"

# Testing
def test_telemetry_analyzer():
    """Test the telemetry analyzer"""
    analyzer = TelemetryAnalyzer()
    
    # Simulate telemetry data
    test_data = {
        'speed': 120,
        'brake_pct': 0,
        'throttle_pct': 80,
        'steering_angle': 0.0,
        'lap_distance_pct': 0.1,
        'gear': 4,
        'rpm': 6000
    }
    
    analysis = analyzer.analyze(test_data)
    print(f"Analysis: {analysis}")
    
    # Simulate corner
    corner_data = test_data.copy()
    corner_data.update({
        'steering_angle': 0.3,
        'speed': 80,
        'brake_pct': 60,
        'lap_distance_pct': 0.25
    })
    
    corner_analysis = analyzer.analyze(corner_data)
    print(f"Corner analysis: {corner_analysis}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_telemetry_analyzer()
