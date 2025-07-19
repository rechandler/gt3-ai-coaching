#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Manager
Manages coaching sessions, tracks progress, and persists data
"""

import json
import time
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class SessionMetrics:
    """Session performance metrics"""
    total_laps: int = 0
    best_lap_time: float = 0.0
    average_lap_time: float = 0.0
    consistency_score: float = 0.0
    improvement_rate: float = 0.0
    total_session_time: float = 0.0
    messages_received: int = 0
    ai_messages: int = 0
    local_messages: int = 0

@dataclass
class SessionData:
    """Complete session data"""
    session_id: str
    start_time: float
    end_time: float = 0.0
    track_name: str = ""
    car_name: str = ""
    session_type: str = ""
    coaching_mode: str = ""
    metrics: SessionMetrics = field(default_factory=SessionMetrics)
    lap_data: List[Dict[str, Any]] = field(default_factory=list)
    coaching_messages: List[Dict[str, Any]] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)

class PerformanceTracker:
    """Tracks performance metrics over time"""
    
    def __init__(self):
        self.lap_times = []
        self.sector_times = {'sector_1': [], 'sector_2': [], 'sector_3': []}
        self.speed_data = []
        self.consistency_data = []
        
    def add_lap(self, lap_time: float, sector_times: List[float] = None):
        """Add a completed lap"""
        self.lap_times.append(lap_time)
        
        if sector_times and len(sector_times) >= 3:
            self.sector_times['sector_1'].append(sector_times[0])
            self.sector_times['sector_2'].append(sector_times[1])
            self.sector_times['sector_3'].append(sector_times[2])
    
    def calculate_improvement_rate(self) -> float:
        """Calculate improvement rate over recent laps"""
        if len(self.lap_times) < 5:
            return 0.0
        
        # Compare first 3 laps with last 3 laps
        early_avg = sum(self.lap_times[:3]) / 3
        recent_avg = sum(self.lap_times[-3:]) / 3
        
        if early_avg > 0:
            improvement = (early_avg - recent_avg) / early_avg
            return improvement
        
        return 0.0
    
    def calculate_consistency(self) -> float:
        """Calculate consistency score"""
        if len(self.lap_times) < 3:
            return 1.0
        
        recent_times = self.lap_times[-10:]  # Last 10 laps
        if len(recent_times) < 3:
            recent_times = self.lap_times
        
        import numpy as np
        variation = np.std(recent_times) / np.mean(recent_times)
        consistency = max(0.0, 1.0 - variation * 5)  # Scale variation
        
        return consistency
    
    def get_best_lap(self) -> float:
        """Get best lap time"""
        return min(self.lap_times) if self.lap_times else 0.0
    
    def get_average_lap(self) -> float:
        """Get average lap time"""
        import numpy as np
        return np.mean(self.lap_times) if self.lap_times else 0.0

class SessionStorage:
    """Handles session data persistence"""
    
    def __init__(self, storage_path: str = "sessions"):
        self.storage_path = storage_path
        self.ensure_storage_directory()
        
    def ensure_storage_directory(self):
        """Ensure storage directory exists"""
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
            logger.info(f"Created storage directory: {self.storage_path}")
    
    def save_session(self, session_data: SessionData) -> bool:
        """Save session data to file"""
        try:
            filename = f"session_{session_data.session_id}.json"
            filepath = os.path.join(self.storage_path, filename)
            
            # Convert to dictionary for JSON serialization
            session_dict = asdict(session_data)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Session saved: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return False
    
    def load_session(self, session_id: str) -> Optional[SessionData]:
        """Load session data from file"""
        try:
            filename = f"session_{session_id}.json"
            filepath = os.path.join(self.storage_path, filename)
            
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                session_dict = json.load(f)
            
            # Convert back to SessionData object
            # Handle nested dataclass conversion
            metrics_dict = session_dict.get('metrics', {})
            session_dict['metrics'] = SessionMetrics(**metrics_dict)
            
            session_data = SessionData(**session_dict)
            logger.info(f"Session loaded: {filepath}")
            return session_data
            
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return None
    
    def list_sessions(self) -> List[str]:
        """List all available session IDs"""
        try:
            sessions = []
            for filename in os.listdir(self.storage_path):
                if filename.startswith('session_') and filename.endswith('.json'):
                    session_id = filename[8:-5]  # Remove 'session_' and '.json'
                    sessions.append(session_id)
            
            return sorted(sessions)
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []
    
    def get_recent_sessions(self, limit: int = 10) -> List[SessionData]:
        """Get recent sessions"""
        try:
            session_ids = self.list_sessions()
            recent_sessions = []
            
            for session_id in session_ids[-limit:]:
                session_data = self.load_session(session_id)
                if session_data:
                    recent_sessions.append(session_data)
            
            # Sort by start time (most recent first)
            recent_sessions.sort(key=lambda x: x.start_time, reverse=True)
            return recent_sessions
            
        except Exception as e:
            logger.error(f"Error getting recent sessions: {e}")
            return []

class SessionManager:
    """Main session management class"""
    
    def __init__(self, storage_path: str = "coaching_sessions"):
        self.storage = SessionStorage(storage_path)
        self.performance_tracker = PerformanceTracker()
        
        # Current session
        self.current_session: Optional[SessionData] = None
        self.session_start_time = 0.0
        
        # Session state
        self.is_active = False
        self.auto_save_interval = 60.0  # Auto-save every minute
        self.last_save_time = 0.0
        
        logger.info("Session Manager initialized")
    
    def start_session(self, track_name: str = "", car_name: str = "", 
                     session_type: str = "practice", coaching_mode: str = "intermediate") -> str:
        """Start a new coaching session"""
        session_id = self.generate_session_id()
        
        self.current_session = SessionData(
            session_id=session_id,
            start_time=time.time(),
            track_name=track_name,
            car_name=car_name,
            session_type=session_type,
            coaching_mode=coaching_mode
        )
        
        self.session_start_time = time.time()
        self.is_active = True
        self.performance_tracker = PerformanceTracker()  # Reset tracker
        
        logger.info(f"Started new session: {session_id}")
        return session_id
    
    def end_session(self) -> Optional[SessionData]:
        """End the current session"""
        if not self.current_session:
            return None
        
        self.current_session.end_time = time.time()
        self.current_session.metrics.total_session_time = (
            self.current_session.end_time - self.current_session.start_time
        )
        
        # Finalize metrics
        self.update_session_metrics()
        
        # Save session
        self.save_session()
        
        session_data = self.current_session
        self.current_session = None
        self.is_active = False
        
        logger.info(f"Ended session: {session_data.session_id}")
        return session_data
    
    async def update_session(self, context: Any):
        """Update session with current context"""
        if not self.current_session or not self.is_active:
            return
        
        try:
            # Update session info from context
            if hasattr(context, 'track_name') and context.track_name:
                self.current_session.track_name = context.track_name
            if hasattr(context, 'car_name') and context.car_name:
                self.current_session.car_name = context.car_name
            if hasattr(context, 'session_type') and context.session_type:
                self.current_session.session_type = context.session_type
            
            # Auto-save periodically
            current_time = time.time()
            if current_time - self.last_save_time > self.auto_save_interval:
                self.save_session()
                self.last_save_time = current_time
                
        except Exception as e:
            logger.error(f"Error updating session: {e}")
    
    def add_lap_data(self, lap_time: float, sector_times: List[float] = None, 
                    telemetry_summary: Dict[str, Any] = None):
        """Add lap completion data"""
        if not self.current_session:
            return
        
        # Add to performance tracker
        self.performance_tracker.add_lap(lap_time, sector_times)
        
        # Add to session data
        lap_data = {
            'lap_number': len(self.current_session.lap_data) + 1,
            'lap_time': lap_time,
            'sector_times': sector_times or [],
            'timestamp': time.time(),
            'telemetry_summary': telemetry_summary or {}
        }
        
        self.current_session.lap_data.append(lap_data)
        self.current_session.metrics.total_laps += 1
        
        # Update metrics
        self.update_session_metrics()
        
        logger.debug(f"Added lap data: {lap_time:.3f}s")
    
    def add_coaching_message(self, message: str, category: str, source: str, 
                           confidence: float = 0.0):
        """Add a coaching message to the session"""
        if not self.current_session:
            return
        
        message_data = {
            'timestamp': time.time(),
            'message': message,
            'category': category,
            'source': source,
            'confidence': confidence
        }
        
        self.current_session.coaching_messages.append(message_data)
        self.current_session.metrics.messages_received += 1
        
        if source == 'remote_ai':
            self.current_session.metrics.ai_messages += 1
        elif source == 'local_ml':
            self.current_session.metrics.local_messages += 1
    
    def update_session_metrics(self):
        """Update session metrics"""
        if not self.current_session:
            return
        
        metrics = self.current_session.metrics
        
        # Update performance metrics
        metrics.best_lap_time = self.performance_tracker.get_best_lap()
        metrics.average_lap_time = self.performance_tracker.get_average_lap()
        metrics.consistency_score = self.performance_tracker.calculate_consistency()
        metrics.improvement_rate = self.performance_tracker.calculate_improvement_rate()
    
    def save_session(self) -> bool:
        """Save current session"""
        if not self.current_session:
            return False
        
        return self.storage.save_session(self.current_session)
    
    def get_recent_performance(self) -> Dict[str, float]:
        """Get recent performance metrics"""
        return {
            'improvement_rate': self.performance_tracker.calculate_improvement_rate(),
            'consistency': self.performance_tracker.calculate_consistency(),
            'best_lap': self.performance_tracker.get_best_lap(),
            'average_lap': self.performance_tracker.get_average_lap(),
            'total_laps': len(self.performance_tracker.lap_times)
        }
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        if not self.current_session:
            return {}
        
        session_time = time.time() - self.current_session.start_time
        
        return {
            'session_id': self.current_session.session_id,
            'session_time': session_time,
            'track_name': self.current_session.track_name,
            'car_name': self.current_session.car_name,
            'metrics': asdict(self.current_session.metrics),
            'performance': self.get_recent_performance()
        }
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{int(time.time() % 1000)}"
    
    def load_previous_session(self, session_id: str) -> Optional[SessionData]:
        """Load a previous session"""
        return self.storage.load_session(session_id)
    
    def get_session_history(self, limit: int = 10) -> List[SessionData]:
        """Get session history"""
        return self.storage.get_recent_sessions(limit)
    
    def export_session_data(self, session_id: str = None) -> Optional[Dict[str, Any]]:
        """Export session data for analysis"""
        if session_id:
            session_data = self.storage.load_session(session_id)
        else:
            session_data = self.current_session
        
        if not session_data:
            return None
        
        return asdict(session_data)

# Testing
async def test_session_manager():
    """Test the session manager"""
    manager = SessionManager("test_sessions")
    
    # Start session
    session_id = manager.start_session(
        track_name="Silverstone",
        car_name="BMW M4 GT3",
        session_type="practice"
    )
    
    print(f"Started session: {session_id}")
    
    # Simulate some laps
    lap_times = [92.5, 91.8, 91.2, 90.9, 91.1]
    for i, lap_time in enumerate(lap_times):
        sector_times = [lap_time/3, lap_time/3, lap_time/3]
        manager.add_lap_data(lap_time, sector_times)
        
        # Add coaching message
        manager.add_coaching_message(
            f"Lap {i+1} completed",
            "lap_completion",
            "local_ml",
            0.8
        )
    
    # Get stats
    stats = manager.get_session_stats()
    print(f"Session stats: {stats}")
    
    # End session
    ended_session = manager.end_session()
    print(f"Session ended: {ended_session.session_id}")
    
    # Test loading
    loaded_session = manager.load_previous_session(session_id)
    if loaded_session:
        print(f"Loaded session: {loaded_session.session_id}")

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_session_manager())
