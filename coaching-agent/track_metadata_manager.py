"""
Track Metadata Manager - Hybrid Approach
=======================================

Handles track segment metadata with:
1. Firebase caching (fastest)
2. Local file fallback (reliable)
3. LLM generation for new tracks (flexible)
"""

import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from project root .env file
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass  # dotenv is optional

# Optional Firebase imports - only import if available
try:
    import firebase_admin
    from firebase_admin import firestore, credentials
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

logger = logging.getLogger(__name__)

class TrackMetadataManager:
    def __init__(self, firebase_config_path: Optional[str] = None):
        self.db = None
        self.local_tracks = {}
        self.local_file_path = "common_tracks.json"
        
        # Initialize Firebase if config provided and Firebase is available
        if firebase_config_path and os.path.exists(firebase_config_path) and FIREBASE_AVAILABLE:
            try:
                cred = credentials.Certificate(firebase_config_path)
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                logger.info("✅ Firebase initialized successfully")
            except Exception as e:
                logger.warning(f"❌ Firebase initialization failed: {e}")
        else:
            if not FIREBASE_AVAILABLE:
                logger.info("⚠️ Firebase not available, using local-only mode")
            else:
                logger.info("⚠️ No Firebase config provided, using local-only mode")
        
        # Load local tracks
        self.load_local_tracks()
        
    def load_local_tracks(self) -> None:
        """Load common tracks from local file"""
        try:
            if os.path.exists(self.local_file_path):
                with open(self.local_file_path, 'r') as f:
                    self.local_tracks = json.load(f)
                logger.info(f"📁 Loaded {len(self.local_tracks)} tracks from local cache")
            else:
                # Initialize with some common tracks
                self.local_tracks = self.get_default_tracks()
                self.save_local_tracks()
                logger.info("📁 Created default local track cache")
        except Exception as e:
            logger.error(f"❌ Failed to load local tracks: {e}")
            self.local_tracks = self.get_default_tracks()
    
    def get_default_tracks(self) -> Dict[str, List[Dict]]:
        """Get default track metadata for common tracks"""
        return {
            "Spa-Francorchamps": [
                {"name": "La Source", "start_pct": 0.00, "end_pct": 0.03, "type": "corner", "description": "Tight right-hander after start/finish"},
                {"name": "Eau Rouge", "start_pct": 0.03, "end_pct": 0.08, "type": "corner", "description": "Famous uphill left-right complex"},
                {"name": "Kemmel Straight", "start_pct": 0.08, "end_pct": 0.15, "type": "straight", "description": "Long uphill straight"},
                {"name": "Les Combes", "start_pct": 0.15, "end_pct": 0.22, "type": "corner", "description": "Medium-speed left-right chicane"},
                {"name": "Bruxelles", "start_pct": 0.22, "end_pct": 0.28, "type": "corner", "description": "Medium-speed left-hander"},
                {"name": "Pouhon", "start_pct": 0.28, "end_pct": 0.35, "type": "corner", "description": "High-speed double-left"},
                {"name": "Fagnes", "start_pct": 0.35, "end_pct": 0.42, "type": "corner", "description": "Medium-speed right-hander"},
                {"name": "Stavelot", "start_pct": 0.42, "end_pct": 0.48, "type": "corner", "description": "High-speed right-hander"},
                {"name": "Blanchimont", "start_pct": 0.48, "end_pct": 0.55, "type": "corner", "description": "High-speed left-hander"},
                {"name": "Bus Stop", "start_pct": 0.55, "end_pct": 0.62, "type": "corner", "description": "Tight chicane before final straight"},
                {"name": "Final Straight", "start_pct": 0.62, "end_pct": 1.00, "type": "straight", "description": "Long straight to finish"}
            ],
            "Nürburgring Grand Prix": [
                {"name": "Turn 1", "start_pct": 0.00, "end_pct": 0.05, "type": "corner", "description": "Tight right-hander"},
                {"name": "Turn 2", "start_pct": 0.05, "end_pct": 0.12, "type": "corner", "description": "Medium-speed left-hander"},
                {"name": "Turn 3", "start_pct": 0.12, "end_pct": 0.18, "type": "corner", "description": "High-speed right-hander"},
                {"name": "Turn 4", "start_pct": 0.18, "end_pct": 0.25, "type": "corner", "description": "Medium-speed left-hander"},
                {"name": "Turn 5", "start_pct": 0.25, "end_pct": 0.32, "type": "corner", "description": "Tight right-hander"},
                {"name": "Turn 6", "start_pct": 0.32, "end_pct": 0.40, "type": "corner", "description": "Medium-speed left-hander"},
                {"name": "Turn 7", "start_pct": 0.40, "end_pct": 0.48, "type": "corner", "description": "High-speed right-hander"},
                {"name": "Turn 8", "start_pct": 0.48, "end_pct": 0.55, "type": "corner", "description": "Medium-speed left-hander"},
                {"name": "Turn 9", "start_pct": 0.55, "end_pct": 0.62, "type": "corner", "description": "Tight right-hander"},
                {"name": "Turn 10", "start_pct": 0.62, "end_pct": 0.70, "type": "corner", "description": "Medium-speed left-hander"},
                {"name": "Turn 11", "start_pct": 0.70, "end_pct": 0.78, "type": "corner", "description": "High-speed right-hander"},
                {"name": "Turn 12", "start_pct": 0.78, "end_pct": 0.85, "type": "corner", "description": "Medium-speed left-hander"},
                {"name": "Turn 13", "start_pct": 0.85, "end_pct": 0.92, "type": "corner", "description": "Tight right-hander"},
                {"name": "Turn 14", "start_pct": 0.92, "end_pct": 1.00, "type": "corner", "description": "Medium-speed left-hander to finish"}
            ],
            "Monza": [
                {"name": "Variante del Rettifilo", "start_pct": 0.00, "end_pct": 0.08, "type": "corner", "description": "Tight chicane after start"},
                {"name": "Curva Grande", "start_pct": 0.08, "end_pct": 0.15, "type": "corner", "description": "High-speed right-hander"},
                {"name": "Variante della Roggia", "start_pct": 0.15, "end_pct": 0.22, "type": "corner", "description": "Medium-speed chicane"},
                {"name": "Curva di Lesmo 1", "start_pct": 0.22, "end_pct": 0.28, "type": "corner", "description": "Medium-speed right-hander"},
                {"name": "Curva di Lesmo 2", "start_pct": 0.28, "end_pct": 0.35, "type": "corner", "description": "Medium-speed left-hander"},
                {"name": "Curva del Serraglio", "start_pct": 0.35, "end_pct": 0.42, "type": "corner", "description": "High-speed right-hander"},
                {"name": "Variante Ascari", "start_pct": 0.42, "end_pct": 0.50, "type": "corner", "description": "Medium-speed chicane"},
                {"name": "Curva Parabolica", "start_pct": 0.50, "end_pct": 0.58, "type": "corner", "description": "Long right-hander"},
                {"name": "Final Straight", "start_pct": 0.58, "end_pct": 1.00, "type": "straight", "description": "Long straight to finish"}
            ]
        }
    
    async def get_track_metadata(self, track_name: str) -> Optional[List[Dict]]:
        """Get track metadata with smart fallback strategy"""
        if not track_name:
            return None
            
        logger.info(f"🔍 Loading metadata for: {track_name}")
        
        # 1. Try Firebase first (fastest if cached)
        firebase_data = await self.get_from_firebase(track_name)
        if firebase_data:
            logger.info(f"☁️ Loaded {track_name} from Firebase cache")
            return firebase_data
        
        # 2. Try local files (reliable)
        local_data = self.local_tracks.get(track_name)
        if local_data:
            logger.info(f"📁 Loaded {track_name} from local cache")
            # Cache in Firebase for next time
            await self.save_to_firebase(track_name, local_data)
            return local_data
        
        # 3. Generate with LLM (flexible but slow)
        logger.info(f"🤖 Generating metadata for {track_name} with LLM...")
        llm_data = await self.generate_with_llm(track_name)
        if llm_data:
            # Cache in Firebase and local
            await self.save_to_firebase(track_name, llm_data)
            self.local_tracks[track_name] = llm_data
            self.save_local_tracks()
            logger.info(f"✅ Generated and cached metadata for {track_name}")
            return llm_data
        
        logger.warning(f"⚠️ No metadata available for {track_name}")
        return None
    
    async def get_from_firebase(self, track_name: str) -> Optional[List[Dict]]:
        """Get track metadata from Firebase"""
        if not self.db or not FIREBASE_AVAILABLE:
            return None
            
        try:
            doc = self.db.collection('track_metadata').document(track_name).get()
            if doc.exists:
                data = doc.to_dict()
                return data.get('segments', [])
        except Exception as e:
            logger.error(f"❌ Firebase error: {e}")
        return None
    
    async def save_to_firebase(self, track_name: str, segments: List[Dict]) -> None:
        """Save track metadata to Firebase"""
        if not self.db or not FIREBASE_AVAILABLE:
            return
            
        try:
            self.db.collection('track_metadata').document(track_name).set({
                'segments': segments,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'track_name': track_name
            })
            logger.debug(f"💾 Saved {track_name} to Firebase")
        except Exception as e:
            logger.error(f"❌ Failed to save to Firebase: {e}")
    
    async def generate_with_llm(self, track_name: str) -> Optional[List[Dict]]:
        """Generate track metadata using LLM"""
        try:
            # Import RemoteAICoach for LLM integration
            from remote_ai_coach import RemoteAICoach
            
            # Create a config for the AI coach with environment API key
            ai_config = {
                'api_key': os.getenv('OPENAI_API_KEY', ''),  # Get from environment
                'model': 'gpt-3.5-turbo',
                'max_requests_per_minute': 5
            }
            
            # Initialize AI coach
            ai_coach = RemoteAICoach(ai_config)
            
            if not ai_coach.is_available():
                logger.warning("🤖 AI coach not available for track metadata generation")
                return None
            
            # Create a mock context for the AI request
            class MockContext:
                def __init__(self, track_name):
                    self.track_name = track_name
                    self.car_name = "GT3 Car"
                    self.session_type = "Practice"
                    self.coaching_mode = "Intermediate"
            
            context = MockContext(track_name)
            
            # Create the insight for track metadata request
            insight = {
                'situation': 'track_metadata_request',
                'confidence': 1.0,
                'data': {
                    'track_name': track_name,
                    'request_type': 'segment_metadata'
                }
            }
            
            # Create mock telemetry (not used for metadata generation)
            mock_telemetry = {
                'track_name': track_name,
                'speed': 0,
                'lap': 1
            }
            
            # Generate the prompt for track metadata
            prompt = f"""
            Generate track segment metadata for the '{track_name}' racing circuit in iRacing.
            
            Return ONLY a valid JSON array of track segments with this exact structure:
            [
                {{
                    "name": "Segment name (e.g., Turn 1, La Source)",
                    "start_pct": 0.0,
                    "end_pct": 0.1,
                    "type": "corner|straight|chicane",
                    "description": "Brief description of the segment"
                }}
            ]
            
            Requirements:
            - Divide the track into 6-10 logical segments (fewer to avoid token limits)
            - Use official turn names where possible (e.g., "Eau Rouge", "La Source")
            - start_pct and end_pct must be between 0.0 and 1.0
            - type must be exactly "corner", "straight", or "chicane"
            - Keep descriptions very brief (max 10 words)
            - Ensure segments cover the entire lap (0.0 to 1.0)
            - Return ONLY the JSON array, no other text
            """
            
            # Make the AI request using raw generation for metadata
            ai_response = await ai_coach.generate_raw(
                prompt,
                "You are a helpful assistant that generates JSON data. Respond only with valid JSON.",
                max_tokens=500  # Higher token limit for complete JSON responses
            )
            
            if ai_response and ai_response.get('message'):
                # Try to parse the JSON response
                try:
                    import json
                    response_text = ai_response['message'].strip()
                    
                    # Clean up the response if it contains markdown or extra text
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]
                    
                    segments = json.loads(response_text)
                    
                    # Validate the segments
                    if isinstance(segments, list) and len(segments) > 0:
                        # Validate each segment
                        valid_segments = []
                        for segment in segments:
                            if (isinstance(segment, dict) and 
                                'name' in segment and 
                                'start_pct' in segment and 
                                'end_pct' in segment and 
                                'type' in segment and 
                                'description' in segment):
                                valid_segments.append(segment)
                        
                        if valid_segments:
                            logger.info(f"✅ Generated {len(valid_segments)} segments for {track_name}")
                            return valid_segments
                        else:
                            logger.warning(f"⚠️ No valid segments found in LLM response for {track_name}")
                    else:
                        logger.warning(f"⚠️ Invalid segment format in LLM response for {track_name}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse LLM JSON response for {track_name}: {e}")
                    logger.error(f"Raw response: {ai_response.get('message', '')}")
                except Exception as e:
                    logger.error(f"❌ Error processing LLM response for {track_name}: {e}")
            else:
                logger.warning(f"🤖 No AI response received for {track_name}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ LLM generation failed for {track_name}: {e}")
            return None
    
    def save_local_tracks(self) -> None:
        """Save updated local tracks to file"""
        try:
            with open(self.local_file_path, 'w') as f:
                json.dump(self.local_tracks, f, indent=2)
            logger.debug("💾 Saved local track cache")
        except Exception as e:
            logger.error(f"❌ Failed to save local tracks: {e}")
    
    def get_available_tracks(self) -> List[str]:
        """Get list of tracks with available metadata"""
        tracks = set(self.local_tracks.keys())
        
        # Could also check Firebase for additional tracks
        # For now, just return local tracks
        return list(tracks)
    
    def get_segment_at_distance(self, track_name: str, lap_dist_pct: float) -> Optional[Dict]:
        """Get the current segment based on lap distance percentage"""
        segments = self.local_tracks.get(track_name, [])
        for segment in segments:
            if segment['start_pct'] <= lap_dist_pct < segment['end_pct']:
                return segment
        return None 