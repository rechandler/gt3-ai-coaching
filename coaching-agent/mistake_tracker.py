#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mistake Tracker - Persistent Mistake Analysis
============================================

Tracks mistake frequency and cost to identify persistent issues that need focus.
Provides session summaries with most common and costly mistakes.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class MistakeEvent:
    """Individual mistake event"""
    mistake_type: str
    corner_id: str
    corner_name: str
    timestamp: float
    severity: float  # 0-1, how bad the mistake was
    time_loss: float  # Seconds lost
    description: str
    data: Dict[str, Any]  # Additional context data

@dataclass
class MistakePattern:
    """Pattern of recurring mistakes"""
    mistake_type: str
    corner_id: str
    corner_name: str
    frequency: int  # How many times it occurred
    total_time_loss: float  # Total time lost
    avg_time_loss: float  # Average time lost per occurrence
    first_occurrence: float  # Timestamp of first occurrence
    last_occurrence: float  # Timestamp of last occurrence
    recent_frequency: int  # Occurrences in last 10 minutes
    severity_trend: str  # 'improving', 'stable', 'declining'
    description: str
    priority: str  # 'critical', 'high', 'medium', 'low'

@dataclass
class SessionSummary:
    """Summary of session mistakes and patterns"""
    session_id: str
    session_start: float
    session_end: float
    total_mistakes: int
    total_time_lost: float
    most_common_mistakes: List[MistakePattern]
    most_costly_mistakes: List[MistakePattern]
    improvement_areas: List[str]
    session_score: float  # 0-1, overall session quality
    recommendations: List[str]

class MistakeClassifier:
    """Classifies mistakes into categories"""
    
    def __init__(self):
        self.mistake_categories = {
            'timing': {
                'late_brake': 'Braking too late',
                'early_brake': 'Braking too early',
                'late_throttle': 'Throttle too late',
                'early_throttle': 'Throttle too early',
                'poor_gear_selection': 'Wrong gear for corner'
            },
            'speed': {
                'low_entry_speed': 'Entry speed too low',
                'high_entry_speed': 'Entry speed too high',
                'low_apex_speed': 'Apex speed too low',
                'high_apex_speed': 'Apex speed too high',
                'low_exit_speed': 'Exit speed too low'
            },
            'technique': {
                'understeer': 'Understeer detected',
                'oversteer': 'Oversteer detected',
                'off_throttle_oversteer': 'Off-throttle oversteer',
                'trail_braking_poor': 'Poor trail braking',
                'inconsistent_inputs': 'Inconsistent inputs'
            },
            'line': {
                'early_apex': 'Apex too early',
                'late_apex': 'Apex too late',
                'poor_racing_line': 'Poor racing line',
                'line_deviation': 'Significant line deviation'
            },
            'consistency': {
                'lap_time_variance': 'Inconsistent lap times',
                'sector_time_variance': 'Inconsistent sector times',
                'input_variance': 'Inconsistent inputs'
            }
        }
    
    def classify_mistake(self, analysis_data: Dict[str, Any]) -> str:
        """Classify a mistake based on analysis data"""
        # Extract key metrics
        brake_timing_delta = analysis_data.get('brake_timing_delta', 0)
        throttle_timing_delta = analysis_data.get('throttle_timing_delta', 0)
        apex_speed_delta = analysis_data.get('apex_speed_delta', 0)
        entry_speed_delta = analysis_data.get('entry_speed_delta', 0)
        exit_speed_delta = analysis_data.get('exit_speed_delta', 0)
        patterns = analysis_data.get('detected_patterns', [])
        total_time_loss = analysis_data.get('total_time_loss', 0)
        
        # Timing mistakes
        if abs(brake_timing_delta) > 0.05:
            return 'late_brake' if brake_timing_delta > 0 else 'early_brake'
        
        if abs(throttle_timing_delta) > 0.05:
            return 'late_throttle' if throttle_timing_delta < 0 else 'early_throttle'
        
        # Speed mistakes
        if abs(apex_speed_delta) > 3.0:
            return 'low_apex_speed' if apex_speed_delta < 0 else 'high_apex_speed'
        
        if abs(entry_speed_delta) > 5.0:
            return 'low_entry_speed' if entry_speed_delta < 0 else 'high_entry_speed'
        
        if abs(exit_speed_delta) > 3.0:
            return 'low_exit_speed' if exit_speed_delta < 0 else 'high_exit_speed'
        
        # Technique mistakes
        if 'understeer' in patterns:
            return 'understeer'
        if 'off_throttle_oversteer' in patterns:
            return 'off_throttle_oversteer'
        if 'inconsistent_inputs' in patterns:
            return 'inconsistent_inputs'
        
        # Line mistakes
        if 'early_apex' in patterns:
            return 'early_apex'
        if 'late_apex' in patterns:
            return 'late_apex'
        
        # Default based on time loss
        if total_time_loss > 0.2:
            return 'poor_racing_line'
        
        return 'general_mistake'
    
    def get_mistake_description(self, mistake_type: str) -> str:
        """Get human-readable description of mistake type"""
        for category, mistakes in self.mistake_categories.items():
            if mistake_type in mistakes:
                return mistakes[mistake_type]
        
        return f"Unknown mistake: {mistake_type}"

class MistakeTracker:
    """Main mistake tracking system"""
    
    def __init__(self, session_id: str = ""):
        self.session_id = session_id or f"session_{int(time.time())}"
        self.mistake_classifier = MistakeClassifier()
        
        # Mistake storage
        self.mistakes: List[MistakeEvent] = []
        self.mistake_patterns: Dict[str, MistakePattern] = {}
        
        # Session tracking
        self.session_start = time.time()
        self.session_end = None
        
        # Analysis windows
        self.recent_window = 600  # 10 minutes for recent frequency
        self.pattern_threshold = 2  # Minimum occurrences to be a pattern
        
        # Priority thresholds
        self.priority_thresholds = {
            'critical': {'frequency': 5, 'avg_time_loss': 0.3},
            'high': {'frequency': 3, 'avg_time_loss': 0.2},
            'medium': {'frequency': 2, 'avg_time_loss': 0.1},
            'low': {'frequency': 1, 'avg_time_loss': 0.05}
        }
        
        logger.info(f"Mistake Tracker initialized for session: {self.session_id}")
    
    def add_mistake(self, analysis_data: Dict[str, Any], corner_id: str = "unknown", 
                   corner_name: str = "Unknown Corner") -> Optional[MistakeEvent]:
        """Add a mistake event from analysis data"""
        try:
            # Only track significant mistakes
            total_time_loss = analysis_data.get('total_time_loss', 0)
            if total_time_loss < 0.05:  # Less than 0.05s loss
                return None
            
            # Classify the mistake
            mistake_type = self.mistake_classifier.classify_mistake(analysis_data)
            
            # Calculate severity (0-1)
            severity = min(1.0, total_time_loss / 0.5)  # Normalize to 0.5s max
            
            # Create mistake event
            mistake = MistakeEvent(
                mistake_type=mistake_type,
                corner_id=corner_id,
                corner_name=corner_name,
                timestamp=time.time(),
                severity=severity,
                time_loss=total_time_loss,
                description=self.mistake_classifier.get_mistake_description(mistake_type),
                data=analysis_data.copy()
            )
            
            # Add to tracking
            self.mistakes.append(mistake)
            
            # Update patterns
            self._update_patterns(mistake)
            
            logger.debug(f"📝 Added mistake: {mistake_type} at {corner_name} ({total_time_loss:.2f}s)")
            
            return mistake
            
        except Exception as e:
            logger.error(f"Error adding mistake: {e}")
            return None
    
    def _update_patterns(self, mistake: MistakeEvent):
        """Update mistake patterns"""
        pattern_key = f"{mistake.mistake_type}_{mistake.corner_id}"
        
        if pattern_key not in self.mistake_patterns:
            # Create new pattern
            self.mistake_patterns[pattern_key] = MistakePattern(
                mistake_type=mistake.mistake_type,
                corner_id=mistake.corner_id,
                corner_name=mistake.corner_name,
                frequency=1,
                total_time_loss=mistake.time_loss,
                avg_time_loss=mistake.time_loss,
                first_occurrence=mistake.timestamp,
                last_occurrence=mistake.timestamp,
                recent_frequency=1,
                severity_trend='stable',
                description=mistake.description,
                priority=self._calculate_priority(mistake.time_loss, 1)
            )
        else:
            # Update existing pattern
            pattern = self.mistake_patterns[pattern_key]
            pattern.frequency += 1
            pattern.total_time_loss += mistake.time_loss
            pattern.avg_time_loss = pattern.total_time_loss / pattern.frequency
            pattern.last_occurrence = mistake.timestamp
            pattern.recent_frequency = self._count_recent_occurrences(pattern_key)
            pattern.severity_trend = self._calculate_severity_trend(pattern)
            pattern.priority = self._calculate_priority(pattern.avg_time_loss, pattern.frequency)
    
    def _count_recent_occurrences(self, pattern_key: str) -> int:
        """Count occurrences in recent window"""
        recent_time = time.time() - self.recent_window
        count = 0
        
        for mistake in self.mistakes:
            if (f"{mistake.mistake_type}_{mistake.corner_id}" == pattern_key and 
                mistake.timestamp >= recent_time):
                count += 1
        
        return count
    
    def _calculate_severity_trend(self, pattern: MistakePattern) -> str:
        """Calculate if severity is improving, stable, or declining"""
        if pattern.frequency < 3:
            return 'stable'
        
        # Get recent mistakes for this pattern
        recent_mistakes = [
            m for m in self.mistakes[-10:]  # Last 10 mistakes
            if f"{m.mistake_type}_{m.corner_id}" == f"{pattern.mistake_type}_{pattern.corner_id}"
        ]
        
        if len(recent_mistakes) < 2:
            return 'stable'
        
        # Compare recent vs older mistakes
        recent_avg = sum(m.time_loss for m in recent_mistakes) / len(recent_mistakes)
        older_mistakes = [
            m for m in self.mistakes[:-10]
            if f"{m.mistake_type}_{m.corner_id}" == f"{pattern.mistake_type}_{pattern.corner_id}"
        ]
        
        if len(older_mistakes) < 2:
            return 'stable'
        
        older_avg = sum(m.time_loss for m in older_mistakes) / len(older_mistakes)
        
        if recent_avg < older_avg * 0.8:
            return 'improving'
        elif recent_avg > older_avg * 1.2:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_priority(self, avg_time_loss: float, frequency: int) -> str:
        """Calculate priority based on frequency and time loss"""
        for priority, thresholds in self.priority_thresholds.items():
            if (frequency >= thresholds['frequency'] and 
                avg_time_loss >= thresholds['avg_time_loss']):
                return priority
        
        return 'low'
    
    def get_persistent_mistakes(self, min_frequency: int = 2) -> List[MistakePattern]:
        """Get persistent mistakes (occurring multiple times)"""
        persistent = [
            pattern for pattern in self.mistake_patterns.values()
            if pattern.frequency >= min_frequency
        ]
        
        # Sort by priority and frequency
        persistent.sort(key=lambda p: (
            self._priority_score(p.priority),
            p.frequency,
            p.total_time_loss
        ), reverse=True)
        
        return persistent
    
    def _priority_score(self, priority: str) -> int:
        """Convert priority to numeric score"""
        scores = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        return scores.get(priority, 0)
    
    def get_session_summary(self) -> SessionSummary:
        """Generate comprehensive session summary"""
        self.session_end = time.time()
        session_duration = self.session_end - self.session_start
        
        # Calculate totals
        total_mistakes = len(self.mistakes)
        total_time_lost = sum(m.time_loss for m in self.mistakes)
        
        # Get persistent mistakes
        persistent_mistakes = self.get_persistent_mistakes()
        
        # Most common mistakes (by frequency)
        most_common = sorted(
            persistent_mistakes,
            key=lambda p: p.frequency,
            reverse=True
        )[:5]
        
        # Most costly mistakes (by total time lost)
        most_costly = sorted(
            persistent_mistakes,
            key=lambda p: p.total_time_loss,
            reverse=True
        )[:5]
        
        # Identify improvement areas
        improvement_areas = self._identify_improvement_areas(persistent_mistakes)
        
        # Calculate session score (0-1, higher is better)
        session_score = self._calculate_session_score(total_mistakes, total_time_lost, session_duration)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(persistent_mistakes, session_score)
        
        summary = SessionSummary(
            session_id=self.session_id,
            session_start=self.session_start,
            session_end=self.session_end,
            total_mistakes=total_mistakes,
            total_time_lost=total_time_lost,
            most_common_mistakes=most_common,
            most_costly_mistakes=most_costly,
            improvement_areas=improvement_areas,
            session_score=session_score,
            recommendations=recommendations
        )
        
        return summary
    
    def _identify_improvement_areas(self, persistent_mistakes: List[MistakePattern]) -> List[str]:
        """Identify key areas for improvement"""
        areas = []
        
        # Group by mistake type
        type_groups = defaultdict(list)
        for pattern in persistent_mistakes:
            type_groups[pattern.mistake_type].append(pattern)
        
        # Identify most problematic areas
        for mistake_type, patterns in type_groups.items():
            total_frequency = sum(p.frequency for p in patterns)
            total_time_lost = sum(p.total_time_loss for p in patterns)
            
            if total_frequency >= 3 or total_time_lost >= 1.0:
                areas.append(f"{self.mistake_classifier.get_mistake_description(mistake_type)} "
                           f"({total_frequency} times, {total_time_lost:.1f}s lost)")
        
        # Add corner-specific issues
        corner_groups = defaultdict(list)
        for pattern in persistent_mistakes:
            corner_groups[pattern.corner_name].append(pattern)
        
        for corner_name, patterns in corner_groups.items():
            total_time_lost = sum(p.total_time_loss for p in patterns)
            if total_time_lost >= 0.5:
                areas.append(f"{corner_name} ({total_time_lost:.1f}s lost)")
        
        return areas[:5]  # Top 5 areas
    
    def _calculate_session_score(self, total_mistakes: int, total_time_lost: float, 
                               session_duration: float) -> float:
        """Calculate session quality score (0-1)"""
        # Base score starts at 1.0
        score = 1.0
        
        # Penalize for mistakes
        if total_mistakes > 0:
            # Penalty based on mistake frequency and severity
            mistake_penalty = min(0.5, total_mistakes * 0.1)  # Max 50% penalty
            time_penalty = min(0.3, total_time_lost / 10.0)   # Max 30% penalty
            score -= (mistake_penalty + time_penalty)
        
        return max(0.0, score)
    
    def _generate_recommendations(self, persistent_mistakes: List[MistakePattern], 
                                session_score: float) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if session_score < 0.5:
            recommendations.append("Focus on consistency - reduce mistake frequency")
        
        # Most critical patterns
        critical_patterns = [p for p in persistent_mistakes if p.priority == 'critical']
        if critical_patterns:
            top_critical = critical_patterns[0]
            recommendations.append(
                f"Priority: Fix {top_critical.corner_name} - "
                f"{self.mistake_classifier.get_mistake_description(top_critical.mistake_type)} "
                f"({top_critical.frequency} times, {top_critical.total_time_loss:.1f}s lost)"
            )
        
        # Most costly patterns
        costly_patterns = sorted(persistent_mistakes, key=lambda p: p.total_time_loss, reverse=True)
        if costly_patterns:
            top_costly = costly_patterns[0]
            if top_costly.total_time_loss >= 1.0:
                recommendations.append(
                    f"Biggest time loss: {top_costly.corner_name} - "
                    f"{top_costly.total_time_loss:.1f}s total"
                )
        
        # Improvement trends
        improving_patterns = [p for p in persistent_mistakes if p.severity_trend == 'improving']
        if improving_patterns:
            recommendations.append(f"Good progress: {len(improving_patterns)} areas improving")
        
        declining_patterns = [p for p in persistent_mistakes if p.severity_trend == 'declining']
        if declining_patterns:
            recommendations.append(f"Watch out: {len(declining_patterns)} areas getting worse")
        
        return recommendations
    
    def get_recent_mistakes(self, window_minutes: int = 10) -> List[MistakeEvent]:
        """Get mistakes from recent time window"""
        cutoff_time = time.time() - (window_minutes * 60)
        return [m for m in self.mistakes if m.timestamp >= cutoff_time]
    
    def get_corner_analysis(self, corner_id: str) -> Dict[str, Any]:
        """Get detailed analysis for a specific corner"""
        corner_mistakes = [m for m in self.mistakes if m.corner_id == corner_id]
        
        if not corner_mistakes:
            return {}
        
        # Group by mistake type
        type_groups = defaultdict(list)
        for mistake in corner_mistakes:
            type_groups[mistake.mistake_type].append(mistake)
        
        analysis = {
            'corner_id': corner_id,
            'corner_name': corner_mistakes[0].corner_name,
            'total_mistakes': len(corner_mistakes),
            'total_time_lost': sum(m.time_loss for m in corner_mistakes),
            'mistake_types': {},
            'recent_trend': self._analyze_corner_trend(corner_mistakes)
        }
        
        for mistake_type, mistakes in type_groups.items():
            analysis['mistake_types'][mistake_type] = {
                'count': len(mistakes),
                'total_time_lost': sum(m.time_loss for m in mistakes),
                'avg_time_loss': sum(m.time_loss for m in mistakes) / len(mistakes),
                'description': self.mistake_classifier.get_mistake_description(mistake_type)
            }
        
        return analysis
    
    def _analyze_corner_trend(self, corner_mistakes: List[MistakeEvent]) -> str:
        """Analyze trend for a specific corner"""
        if len(corner_mistakes) < 3:
            return 'insufficient_data'
        
        # Split into recent and older mistakes
        mid_point = len(corner_mistakes) // 2
        recent_mistakes = corner_mistakes[mid_point:]
        older_mistakes = corner_mistakes[:mid_point]
        
        recent_avg = sum(m.time_loss for m in recent_mistakes) / len(recent_mistakes)
        older_avg = sum(m.time_loss for m in older_mistakes) / len(older_mistakes)
        
        if recent_avg < older_avg * 0.8:
            return 'improving'
        elif recent_avg > older_avg * 1.2:
            return 'declining'
        else:
            return 'stable'
    
    def export_data(self, filepath: str = "") -> Dict[str, Any]:
        """Export tracking data"""
        if not filepath:
            filepath = f"mistake_tracking_{self.session_id}.json"
        
        data = {
            'session_id': self.session_id,
            'session_start': self.session_start,
            'session_end': self.session_end,
            'mistakes': [
                {
                    'mistake_type': m.mistake_type,
                    'corner_id': m.corner_id,
                    'corner_name': m.corner_name,
                    'timestamp': m.timestamp,
                    'severity': m.severity,
                    'time_loss': m.time_loss,
                    'description': m.description
                }
                for m in self.mistakes
            ],
            'patterns': [
                {
                    'mistake_type': p.mistake_type,
                    'corner_id': p.corner_id,
                    'corner_name': p.corner_name,
                    'frequency': p.frequency,
                    'total_time_loss': p.total_time_loss,
                    'avg_time_loss': p.avg_time_loss,
                    'priority': p.priority,
                    'severity_trend': p.severity_trend
                }
                for p in self.mistake_patterns.values()
            ]
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"💾 Exported mistake tracking data to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
        
        return data

# Testing
def test_mistake_tracker():
    """Test the mistake tracker"""
    tracker = MistakeTracker("test_session")
    
    # Simulate some mistakes
    test_mistakes = [
        {
            'brake_timing_delta': 0.1,
            'throttle_timing_delta': 0.0,
            'apex_speed_delta': -5.0,
            'total_time_loss': 0.3,
            'detected_patterns': ['late_brake']
        },
        {
            'brake_timing_delta': 0.08,
            'throttle_timing_delta': 0.0,
            'apex_speed_delta': -3.0,
            'total_time_loss': 0.25,
            'detected_patterns': ['late_brake']
        },
        {
            'brake_timing_delta': 0.0,
            'throttle_timing_delta': -0.1,
            'apex_speed_delta': 0.0,
            'total_time_loss': 0.2,
            'detected_patterns': ['late_throttle']
        }
    ]
    
    # Add mistakes
    for i, mistake_data in enumerate(test_mistakes):
        tracker.add_mistake(
            mistake_data,
            corner_id=f"turn_{i+1}",
            corner_name=f"Turn {i+1}"
        )
    
    # Get persistent mistakes
    persistent = tracker.get_persistent_mistakes()
    print(f"Persistent mistakes: {len(persistent)}")
    for pattern in persistent:
        print(f"  {pattern.corner_name}: {pattern.mistake_type} "
              f"({pattern.frequency} times, {pattern.total_time_loss:.1f}s lost)")
    
    # Get session summary
    summary = tracker.get_session_summary()
    print(f"\nSession Summary:")
    print(f"  Total mistakes: {summary.total_mistakes}")
    print(f"  Total time lost: {summary.total_time_lost:.1f}s")
    print(f"  Session score: {summary.session_score:.2f}")
    print(f"  Recommendations: {summary.recommendations}")

if __name__ == "__main__":
    test_mistake_tracker() 