#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reference Lap Helper
===================

Helper functions for managing reference laps and updating them when
personal bests or better sectors occur. This module provides utilities for:

1. Automatic reference lap updates when PBs occur
2. Sector-by-sector reference tracking
3. Persistence of good reference laps per car/track
4. Professional comparison data management
"""

import time
import logging
from typing import Dict, List, Optional, Any
from lap_buffer_manager import LapBufferManager, LapData, ReferenceLap
from message_queue import CoachingMessage, MessagePriority

logger = logging.getLogger(__name__)

class ReferenceLapHelper:
    """Helper for managing reference laps and automatic updates"""
    
    def __init__(self, lap_buffer_manager: LapBufferManager):
        self.lap_buffer_manager = lap_buffer_manager
        self.reference_update_callbacks = []
        
    def register_reference_update_callback(self, callback):
        """Register a callback to be called when reference laps are updated"""
        self.reference_update_callbacks.append(callback)
    
    def check_and_update_reference_laps(self, lap_data: LapData) -> Dict[str, Any]:
        """Check if lap qualifies as a new reference and update accordingly"""
        updates = {
            'personal_best_updated': False,
            'session_best_updated': False,
            'sector_bests_updated': [],
            'new_references_created': []
        }
        
        try:
            # Check for new personal best
            if self._is_new_personal_best(lap_data):
                self._update_personal_best_reference(lap_data)
                updates['personal_best_updated'] = True
                self._notify_reference_update('personal_best', lap_data)
            
            # Check for new session best
            if self._is_new_session_best(lap_data):
                self._update_session_best_reference(lap_data)
                updates['session_best_updated'] = True
                self._notify_reference_update('session_best', lap_data)
            
            # Check for new sector bests
            sector_updates = self._check_sector_bests(lap_data)
            if sector_updates:
                updates['sector_bests_updated'] = sector_updates
                self._notify_reference_update('sector_bests', lap_data)
            
            # Create additional reference types if lap is good enough
            new_references = self._create_additional_references(lap_data)
            if new_references:
                updates['new_references_created'] = new_references
            
            logger.info(f"Reference lap updates: {updates}")
            return updates
            
        except Exception as e:
            logger.error(f"Error updating reference laps: {e}")
            return updates
    
    def _is_new_personal_best(self, lap_data: LapData) -> bool:
        """Check if lap is a new personal best"""
        if not self.lap_buffer_manager.personal_best_lap:
            return True
        
        return lap_data.lap_time < self.lap_buffer_manager.personal_best_lap.lap_time
    
    def _is_new_session_best(self, lap_data: LapData) -> bool:
        """Check if lap is a new session best"""
        if not self.lap_buffer_manager.session_best_lap:
            return True
        
        return lap_data.lap_time < self.lap_buffer_manager.session_best_lap.lap_time
    
    def _update_personal_best_reference(self, lap_data: LapData):
        """Update personal best reference"""
        self.lap_buffer_manager.personal_best_lap = lap_data
        self.lap_buffer_manager.save_reference_lap(lap_data, 'personal_best')
        logger.info(f"🏆 New personal best reference: {lap_data.lap_time:.3f}s")
    
    def _update_session_best_reference(self, lap_data: LapData):
        """Update session best reference"""
        self.lap_buffer_manager.session_best_lap = lap_data
        self.lap_buffer_manager.save_reference_lap(lap_data, 'session_best')
        logger.info(f"🥇 New session best reference: {lap_data.lap_time:.3f}s")
    
    def _check_sector_bests(self, lap_data: LapData) -> List[Dict[str, Any]]:
        """Check for new sector bests"""
        sector_updates = []
        
        for i, sector_time in enumerate(lap_data.sector_times):
            if i >= len(self.lap_buffer_manager.best_sector_times):
                continue
            
            if sector_time < self.lap_buffer_manager.best_sector_times[i]:
                sector_updates.append({
                    'sector': i + 1,
                    'old_time': self.lap_buffer_manager.best_sector_times[i],
                    'new_time': sector_time,
                    'improvement': self.lap_buffer_manager.best_sector_times[i] - sector_time
                })
                self.lap_buffer_manager.best_sector_times[i] = sector_time
        
        return sector_updates
    
    def _create_additional_references(self, lap_data: LapData) -> List[str]:
        """Create additional reference types for good laps"""
        new_references = []
        
        # Create "optimal" reference if lap is very good
        if self._is_optimal_lap(lap_data):
            self.lap_buffer_manager.save_reference_lap(lap_data, 'optimal')
            new_references.append('optimal')
        
        # Create "consistency" reference if lap shows good consistency
        if self._is_consistent_lap(lap_data):
            self.lap_buffer_manager.save_reference_lap(lap_data, 'consistency')
            new_references.append('consistency')
        
        # Create "race_pace" reference if lap is good for race conditions
        if self._is_race_pace_lap(lap_data):
            self.lap_buffer_manager.save_reference_lap(lap_data, 'race_pace')
            new_references.append('race_pace')
        
        return new_references
    
    def _is_optimal_lap(self, lap_data: LapData) -> bool:
        """Check if lap qualifies as optimal reference"""
        if not self.lap_buffer_manager.personal_best_lap:
            return True
        
        # Lap is optimal if it's within 0.5% of personal best
        pb_time = self.lap_buffer_manager.personal_best_lap.lap_time
        optimal_threshold = pb_time * 1.005
        
        return lap_data.lap_time <= optimal_threshold
    
    def _is_consistent_lap(self, lap_data: LapData) -> bool:
        """Check if lap shows good consistency"""
        if len(self.lap_buffer_manager.completed_laps) < 3:
            return False
        
        # Calculate consistency with recent laps
        recent_laps = self.lap_buffer_manager.completed_laps[-5:]
        lap_times = [lap.lap_time for lap in recent_laps]
        
        # Lap is consistent if variation is less than 1%
        avg_time = sum(lap_times) / len(lap_times)
        variation = max(lap_times) - min(lap_times)
        consistency_threshold = avg_time * 0.01
        
        return variation <= consistency_threshold
    
    def _is_race_pace_lap(self, lap_data: LapData) -> bool:
        """Check if lap is good for race pace reference"""
        if not self.lap_buffer_manager.personal_best_lap:
            return True
        
        # Race pace is typically 1-2% slower than qualifying pace
        pb_time = self.lap_buffer_manager.personal_best_lap.lap_time
        race_pace_threshold = pb_time * 1.02
        
        return lap_data.lap_time <= race_pace_threshold
    
    def _notify_reference_update(self, update_type: str, lap_data: LapData):
        """Notify registered callbacks of reference updates"""
        for callback in self.reference_update_callbacks:
            try:
                callback(update_type, lap_data)
            except Exception as e:
                logger.error(f"Error in reference update callback: {e}")
    
    def get_reference_comparison_summary(self, reference_type: str = 'personal_best') -> Dict[str, Any]:
        """Get a summary of current performance vs reference"""
        comparison = self.lap_buffer_manager.get_reference_comparison(reference_type)
        if not comparison:
            return {}
        
        ref_lap = comparison['reference_lap_data']
        current_progress = self.lap_buffer_manager.get_current_lap_progress()
        
        summary = {
            'reference_type': reference_type,
            'reference_lap_time': ref_lap.lap_time,
            'current_elapsed': current_progress.get('elapsed_time', 0),
            'delta_to_reference': comparison['delta_to_reference'],
            'is_ahead': comparison['is_ahead'],
            'sector_comparisons': []
        }
        
        # Add sector-by-sector comparison
        for i, sector_delta in enumerate(comparison['sector_deltas']):
            if i < len(ref_lap.sector_times):
                summary['sector_comparisons'].append({
                    'sector': i + 1,
                    'reference_time': ref_lap.sector_times[i],
                    'current_time': current_progress.get('sector_times', [])[i] if i < len(current_progress.get('sector_times', [])) else 0,
                    'delta': sector_delta
                })
        
        return summary
    
    def get_rolling_stint_analysis(self) -> Dict[str, Any]:
        """Get rolling stint analysis for race pace coaching"""
        return self.lap_buffer_manager.get_rolling_stint_analysis()
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary with reference data"""
        summary = self.lap_buffer_manager.get_session_summary()
        
        # Add reference lap information
        summary['reference_laps'] = {
            'personal_best': self.lap_buffer_manager.personal_best_lap.lap_time if self.lap_buffer_manager.personal_best_lap else None,
            'session_best': self.lap_buffer_manager.session_best_lap.lap_time if self.lap_buffer_manager.session_best_lap else None,
            'available_references': list(self.lap_buffer_manager.reference_laps.keys())
        }
        
        return summary

def create_reference_lap_helper(lap_buffer_manager: LapBufferManager) -> ReferenceLapHelper:
    """Factory function to create a reference lap helper"""
    return ReferenceLapHelper(lap_buffer_manager)

# Example usage and integration
async def integrate_with_coaching_agent(coaching_agent):
    """Example of how to integrate reference lap helper with coaching agent"""
    
    # Create helper
    helper = create_reference_lap_helper(coaching_agent.lap_buffer_manager)
    
    # Register callback for reference updates
    def on_reference_update(update_type: str, lap_data: LapData):
        if update_type == 'personal_best':
            # Send congratulatory message
            coaching_agent.message_queue.add_message(
                CoachingMessage(
                    content=f"🏆 CONGRATULATIONS! New personal best: {lap_data.lap_time:.3f}s",
                    category="achievement",
                    priority=MessagePriority.HIGH,
                    source="reference_helper",
                    confidence=1.0,
                    context="personal_best",
                    timestamp=time.time()
                )
            )
        elif update_type == 'sector_bests':
            # Send sector improvement message
            coaching_agent.message_queue.add_message(
                CoachingMessage(
                    content=f"📊 New sector best achieved!",
                    category="achievement",
                    priority=MessagePriority.MEDIUM,
                    source="reference_helper",
                    confidence=1.0,
                    context="sector_best",
                    timestamp=time.time()
                )
            )
    
    helper.register_reference_update_callback(on_reference_update)
    
    return helper 