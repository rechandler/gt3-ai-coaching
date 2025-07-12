#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Persistence for GT3 AI Coach
Handles saving/loading session data with hybrid local/cloud approach
"""

import json
import os
import time
import logging
import asyncio
import threading
import queue
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SessionData:
    """Complete session data for persistence"""
    session_id: str
    track_name: str
    car_name: str
    start_time: float
    end_time: Optional[float] = None
    
    # Performance data
    laps: List[Dict] = field(default_factory=list)  # Serialized LapData
    best_lap_time: Optional[float] = None
    best_lap_number: Optional[int] = None
    
    # AI learning data
    baseline_established: bool = False
    driving_style: str = "unknown"
    coaching_intensity: float = 1.0
    consistency_threshold: float = 0.05
    
    # Track-specific learned patterns
    corner_analysis: Dict[str, Dict] = field(default_factory=dict)
    brake_point_history: Dict[str, List] = field(default_factory=dict)
    speed_history: Dict[str, List] = field(default_factory=dict)
    track_learning: Dict[str, Any] = field(default_factory=dict)
    
    # Vehicle dynamics learning
    optimal_shift_rpm_ranges: Dict[int, tuple] = field(default_factory=dict)
    gear_shift_history: List[Dict] = field(default_factory=list)
    
    # Session stats
    total_distance: float = 0.0
    total_incidents: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary (JSON deserialization)"""
        return cls(**data)

class SessionPersistenceManager:
    """Manages local and cloud session persistence with hybrid approach"""
    
    def __init__(self, data_dir: str = "coaching_data", cloud_sync_enabled: bool = False):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Local persistence
        self.sessions_index_file = self.data_dir / "sessions_index.json"
        self.sessions_cache: Dict[str, SessionData] = {}
        
        # Cloud sync (optional)
        self.cloud_sync_enabled = cloud_sync_enabled
        self.sync_queue = queue.Queue() if cloud_sync_enabled else None
        self.sync_thread = None
        
        # Load existing sessions index
        self._load_sessions_index()
        
        # Start cloud sync thread if enabled
        if self.cloud_sync_enabled:
            self._start_sync_thread()
        
        logger.info(f"📁 Session persistence initialized - Local: {self.data_dir}, Cloud: {cloud_sync_enabled}")
    
    def create_session(self, track_name: str, car_name: str) -> SessionData:
        """Create a new session"""
        session_id = f"{track_name}_{car_name}_{int(time.time())}"
        
        session = SessionData(
            session_id=session_id,
            track_name=track_name,
            car_name=car_name,
            start_time=time.time()
        )
        
        # Save immediately
        self.save_session(session)
        self.sessions_cache[session_id] = session
        
        logger.info(f"📝 New session created: {session_id}")
        return session
    
    def save_session(self, session: SessionData) -> bool:
        """Save session locally (and queue for cloud sync)"""
        try:
            # Save to local file
            session_file = self.data_dir / f"{session.session_id}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Update sessions cache
            self.sessions_cache[session.session_id] = session
            
            # Update sessions index
            self._update_sessions_index(session)
            
            # Queue for cloud sync if enabled
            if self.cloud_sync_enabled and self.sync_queue:
                self.sync_queue.put(('save', session.session_id))
            
            logger.debug(f"💾 Session saved: {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            return False
    
    def load_session(self, session_id: str) -> Optional[SessionData]:
        """Load session from local storage"""
        try:
            # Check cache first
            if session_id in self.sessions_cache:
                return self.sessions_cache[session_id]
            
            # Load from file
            session_file = self.data_dir / f"{session_id}.json"
            if not session_file.exists():
                logger.warning(f"Session file not found: {session_id}")
                return None
            
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session = SessionData.from_dict(data)
            self.sessions_cache[session_id] = session
            
            logger.info(f"📖 Session loaded: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    def find_previous_sessions(self, track_name: str, car_name: str, limit: int = 10) -> List[SessionData]:
        """Find previous sessions for the same track/car combination"""
        matching_sessions = []
        
        # Check sessions index
        sessions_index = self._load_sessions_index()
        
        for session_info in sessions_index.get('sessions', []):
            if (session_info.get('track_name') == track_name and 
                session_info.get('car_name') == car_name):
                
                session = self.load_session(session_info['session_id'])
                if session:
                    matching_sessions.append(session)
        
        # Sort by start time (newest first)
        matching_sessions.sort(key=lambda s: s.start_time, reverse=True)
        
        return matching_sessions[:limit]
    
    def get_track_baseline(self, track_name: str, car_name: str) -> Optional[Dict[str, Any]]:
        """Get established baseline for track/car combination"""
        previous_sessions = self.find_previous_sessions(track_name, car_name, limit=5)
        
        if not previous_sessions:
            return None
        
        # Find the most recent session with established baseline
        for session in previous_sessions:
            if session.baseline_established and session.best_lap_time:
                return {
                    'best_lap_time': session.best_lap_time,
                    'driving_style': session.driving_style,
                    'consistency_threshold': session.consistency_threshold,
                    'corner_analysis': session.corner_analysis,
                    'track_learning': session.track_learning,
                    'session_id': session.session_id
                }
        
        return None
    
    def reset_baseline(self, track_name: str, car_name: str) -> bool:
        """Reset baseline for track/car combination"""
        try:
            sessions = self.find_previous_sessions(track_name, car_name)
            
            for session in sessions:
                session.baseline_established = False
                session.driving_style = "unknown"
                session.consistency_threshold = 0.05
                session.corner_analysis.clear()
                session.track_learning.clear()
                self.save_session(session)
            
            logger.info(f"🔄 Baseline reset for {track_name} + {car_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset baseline: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session locally and from cloud"""
        try:
            session_file = self.data_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
            
            if session_id in self.sessions_cache:
                del self.sessions_cache[session_id]
            
            self._remove_from_sessions_index(session_id)
            
            if self.cloud_sync_enabled and self.sync_queue:
                self.sync_queue.put(('delete', session_id))
            
            logger.info(f"🗑️ Session deleted: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def _load_sessions_index(self) -> Dict[str, Any]:
        """Load sessions index from file"""
        try:
            if self.sessions_index_file.exists():
                with open(self.sessions_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load sessions index: {e}")
        
        return {'sessions': [], 'last_updated': time.time()}
    
    def _save_sessions_index(self) -> None:
        """Save sessions index to file"""
        try:
            index_data = self._build_sessions_index()
            with open(self.sessions_index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save sessions index: {e}")
    
    def _build_sessions_index(self) -> Dict[str, Any]:
        """Build sessions index from cached sessions"""
        sessions_list = []
        
        for session_id, session in self.sessions_cache.items():
            sessions_list.append({
                'session_id': session_id,
                'track_name': session.track_name,
                'car_name': session.car_name,
                'start_time': session.start_time,
                'end_time': session.end_time,
                'best_lap_time': session.best_lap_time,
                'baseline_established': session.baseline_established
            })
        
        return {
            'sessions': sessions_list,
            'last_updated': time.time()
        }
    
    def _update_sessions_index(self, session: SessionData):
        """Update sessions index with new/modified session"""
        self._save_sessions_index()
    
    def _remove_from_sessions_index(self, session_id: str):
        """Remove session from index"""
        self._save_sessions_index()
    
    def _start_sync_thread(self):
        """Start background thread for cloud synchronization"""
        if not self.cloud_sync_enabled or not self.sync_queue:
            return
        
        def sync_worker():
            while True:
                try:
                    operation, session_id = self.sync_queue.get(timeout=1)
                    
                    if operation == 'save':
                        self._sync_to_cloud(session_id)
                    elif operation == 'delete':
                        self._delete_from_cloud(session_id)
                    
                    self.sync_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Cloud sync error: {e}")
        
        self.sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self.sync_thread.start()
        logger.info("☁️ Cloud sync thread started")
    
    def _sync_to_cloud(self, session_id: str):
        """Sync session to cloud storage (Firebase implementation)"""
        try:
            session = self.sessions_cache.get(session_id)
            if not session:
                return
            
            # Example: Firebase Firestore sync
            # Uncomment and configure if you want to use Firebase:
            """
            import firebase_admin
            from firebase_admin import credentials, firestore
            
            # Initialize Firebase (do this once in __init__)
            if not firebase_admin._apps:
                cred = credentials.Certificate("path/to/serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
            
            db = firestore.client()
            
            # Save session to Firestore
            doc_ref = db.collection('gt3_sessions').document(session_id)
            doc_ref.set(session.to_dict())
            
            logger.info(f"☁️ Synced session to Firebase: {session_id}")
            """
            
            # Example: Simple file upload to cloud storage
            # You can implement any cloud provider here:
            """
            # AWS S3
            import boto3
            s3 = boto3.client('s3')
            s3.put_object(
                Bucket='gt3-coaching-data',
                Key=f'sessions/{session_id}.json',
                Body=json.dumps(session.to_dict())
            )
            
            # Google Cloud Storage
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket('gt3-coaching-data')
            blob = bucket.blob(f'sessions/{session_id}.json')
            blob.upload_from_string(json.dumps(session.to_dict()))
            
            # Azure Blob Storage
            from azure.storage.blob import BlobServiceClient
            blob_service = BlobServiceClient(account_url="https://account.blob.core.windows.net")
            blob_client = blob_service.get_blob_client(
                container="gt3-coaching", 
                blob=f"sessions/{session_id}.json"
            )
            blob_client.upload_blob(json.dumps(session.to_dict()))
            """
            
            logger.debug(f"☁️ Would sync to cloud: {session_id} (implementation needed)")
            
        except Exception as e:
            logger.error(f"Failed to sync session {session_id} to cloud: {e}")
    
    def _delete_from_cloud(self, session_id: str):
        """Delete session from cloud storage"""
        try:
            # Example implementations for different providers:
            """
            # Firebase
            db = firestore.client()
            db.collection('gt3_sessions').document(session_id).delete()
            
            # AWS S3
            s3.delete_object(Bucket='gt3-coaching-data', Key=f'sessions/{session_id}.json')
            
            # Google Cloud
            bucket.blob(f'sessions/{session_id}.json').delete()
            
            # Azure
            blob_client.delete_blob()
            """
            
            logger.debug(f"☁️ Would delete from cloud: {session_id} (implementation needed)")
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id} from cloud: {e}")
    
    def setup_firebase_sync(self, service_account_path: str):
        """Setup Firebase cloud sync with service account"""
        try:
            import firebase_admin
            from firebase_admin import credentials
            
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            
            self.cloud_provider = "firebase"
            self.enable_cloud_sync()
            logger.info("🔥 Firebase cloud sync enabled")
            return True
            
        except ImportError:
            logger.error("Firebase Admin SDK not installed. Run: pip install firebase-admin")
            return False
        except Exception as e:
            logger.error(f"Failed to setup Firebase: {e}")
            return False
    
    def setup_aws_sync(self, aws_config: Dict[str, str]):
        """Setup AWS S3 cloud sync"""
        try:
            import boto3
            
            # Configure AWS credentials
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_config.get('access_key'),
                aws_secret_access_key=aws_config.get('secret_key'),
                region_name=aws_config.get('region', 'us-east-1')
            )
            self.s3_bucket = aws_config.get('bucket_name')
            
            self.cloud_provider = "aws_s3"
            self.enable_cloud_sync()
            logger.info("🏗️ AWS S3 cloud sync enabled")
            return True
            
        except ImportError:
            logger.error("Boto3 not installed. Run: pip install boto3")
            return False
        except Exception as e:
            logger.error(f"Failed to setup AWS S3: {e}")
            return False
    
    def enable_cloud_sync(self, cloud_config: Optional[Dict[str, Any]] = None):
        """Enable cloud synchronization"""
        if not self.cloud_sync_enabled:
            self.cloud_sync_enabled = True
            self.sync_queue = queue.Queue()
            self._start_sync_thread()
            logger.info("☁️ Cloud sync enabled")
    
    def disable_cloud_sync(self):
        """Disable cloud synchronization"""
        self.cloud_sync_enabled = False
        if self.sync_queue:
            # Finish pending sync operations
            self.sync_queue.join()
        logger.info("☁️ Cloud sync disabled")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about stored sessions"""
        sessions_index = self._load_sessions_index()
        sessions = sessions_index.get('sessions', [])
        
        if not sessions:
            return {'total_sessions': 0}
        
        # Calculate stats
        total_sessions = len(sessions)
        tracks = set(s.get('track_name', 'unknown') for s in sessions)
        cars = set(s.get('car_name', 'unknown') for s in sessions)
        
        # Find best lap times per track
        track_bests = {}
        for session in sessions:
            track = session.get('track_name', 'unknown')
            best_time = session.get('best_lap_time')
            if best_time and (track not in track_bests or best_time < track_bests[track]):
                track_bests[track] = best_time
        
        return {
            'total_sessions': total_sessions,
            'unique_tracks': len(tracks),
            'unique_cars': len(cars),
            'tracks': list(tracks),
            'cars': list(cars),
            'track_best_times': track_bests,
            'storage_path': str(self.data_dir),
            'cloud_sync_enabled': self.cloud_sync_enabled
        }
