#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GT3 AI Coaching - Separate Coaching Messages Server
Handles only AI coaching messages, separate from telemetry
"""

import asyncio
import json
import logging
import websockets
import time
from typing import Dict, Any, Optional, Set
import sys
import io

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import the simplified AI coach and session persistence
from ai_coach_simple import LocalAICoach
from session_persistence import SessionPersistenceManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CoachingServer:
    def __init__(self):
        # Connected clients
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Initialize AI Coach with session persistence
        self.ai_coach = LocalAICoach(
            data_dir="coaching_data",
            cloud_sync_enabled=False  # Can be enabled later
        )
        
        # Initialize session persistence
        self.session_persistence = SessionPersistenceManager(
            data_dir="coaching_data",
            cloud_sync_enabled=False
        )
        
        # Message queue and history
        self.message_queue = []
        self.last_message_id = 0
        
        # Telemetry data cache (received from telemetry server)
        self.latest_telemetry = None
        self.telemetry_updated = False
        
        # Session state
        self.current_session_active = False
        self.last_message_time = 0.0  # Add missing last_message_time
        self.session_start_announced = False  # Track if we've announced session start
        self.last_session_check_time = 0.0  # Limit session change checks
        
        logger.info("🧠 GT3 AI Coaching Server initialized with session persistence")
    
    async def register_client(self, websocket):
        """Register a new coaching client"""
        self.clients.add(websocket)
        logger.info(f"🔗 Coaching client connected from {websocket.remote_address}")
        
        # Send any recent messages to new client
        if self.message_queue:
            recent_messages = self.message_queue[-5:]  # Last 5 messages
            for msg in recent_messages:
                try:
                    await websocket.send(json.dumps(msg))
                except websockets.exceptions.ConnectionClosed:
                    break
    
    async def unregister_client(self, websocket):
        """Unregister a coaching client"""
        self.clients.discard(websocket)
        logger.info(f"❌ Coaching client disconnected")
    
    async def broadcast_message(self, message_data, message_type="coaching"):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
        
        # Create message with unique ID
        self.last_message_id += 1
        message = {
            "type": message_type,
            "id": self.last_message_id,
            "timestamp": time.time(),
            "data": message_data
        }
        
        # Add to queue only if it's a coaching message (keep last 50 messages)
        if message_type == "coaching":
            self.message_queue.append(message)
            if len(self.message_queue) > 50:
                self.message_queue.pop(0)
        
        # Broadcast to all clients
        disconnected_clients = set()
        message_json = json.dumps(message)
        
        for client in self.clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.discard(client)
        
        # Log differently based on message type
        if message_type == "coaching":
            logger.info(f"📢 Broadcasted coaching message to {len(self.clients)} clients: {message_data.get('message', '')[:50]}...")
        else:
            logger.debug(f"📢 Broadcasted {message_type} to {len(self.clients)} clients")
    
    async def receive_telemetry(self, websocket, path):
        """Receive telemetry data from telemetry server"""
        logger.info("📊 Telemetry data receiver connected")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    if data.get('type') == 'telemetry':
                        self.latest_telemetry = data.get('data')
                        self.telemetry_updated = True
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from telemetry server")
                except Exception as e:
                    logger.error(f"Error processing telemetry: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("📊 Telemetry receiver disconnected")
        except Exception as e:
            logger.error(f"Telemetry receiver error: {e}")
    
    async def handle_coaching_client(self, websocket, path=None):
        """Handle coaching client connections"""
        await self.register_client(websocket)
        
        try:
            # Keep connection alive and handle any incoming messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    # Handle client requests (e.g., get message history)
                    if data.get('type') == 'get_history':
                        count = min(data.get('count', 10), 50)
                        history = self.message_queue[-count:] if count > 0 else []
                        
                        response = {
                            "type": "history",
                            "messages": history
                        }
                        await websocket.send(json.dumps(response))
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from coaching client")
                except Exception as e:
                    logger.error(f"Error handling coaching client message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Coaching client error: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def ai_processing_loop(self):
        """Main AI processing loop - now handles telemetry via WebSocket server"""
        logger.info("🤖 AI processing loop started - waiting for telemetry connections")
        
        # Just keep the loop alive - actual processing happens in handle_telemetry_connection
        while True:
            await asyncio.sleep(10)  # Keep loop alive
        
    def reset_session_state(self):
        """Reset session state when session changes"""
        self.current_session_active = False
        self.session_start_announced = False
        self.session_persistence.current_session_id = None
        self.last_session_check_time = 0.0
        logger.info("🔄 Session state reset")
    
    def detect_session_change(self, telemetry_data):
        """Detect if we've changed sessions and need to reset"""
        try:
            current_track = telemetry_data.get('trackName', 'Unknown Track')
            current_car = telemetry_data.get('carName', 'Unknown Car')
            
            # If we have an active session, check if track/car changed
            if hasattr(self.ai_coach, 'track_name') and hasattr(self.ai_coach, 'car_name'):
                # Only trigger session change if we're moving from one known session to another
                if (self.ai_coach.track_name != "unknown" and self.ai_coach.car_name != "unknown" and
                    (current_track != self.ai_coach.track_name or current_car != self.ai_coach.car_name)):
                    logger.info(f"🔄 Session change detected: {self.ai_coach.track_name}/{self.ai_coach.car_name} → {current_track}/{current_car}")
                    self.reset_session_state()
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error detecting session change: {e}")
            return False

    async def _try_start_session(self, telemetry_data):
        """Try to auto-start a session based on telemetry data"""
        try:
            # Check if session is already active or announced
            if self.session_persistence.current_session_id and self.session_start_announced:
                return  # Session already started and announced
            
            # Extract track and car info - prioritize WeekendInfo data
            track_display_name = telemetry_data.get('TrackDisplayName', 'Unknown Track')  # Capital T for iRacing
            track_name = telemetry_data.get('TrackName', track_display_name)  # Capital T for iRacing
            car_name = telemetry_data.get('CarScreenName', telemetry_data.get('CarName', 'Unknown Car'))  # Capital C for iRacing
            
            # Log what we got
            logger.debug(f"Session info from telemetry: track='{track_name}', car='{car_name}'")
            
            # Only start if we have valid data and car is moving
            speed = telemetry_data.get('Speed', 0)  # Capital S for iRacing field
            if speed > 5 and track_name not in ['Unknown Track', 'iRacing Track']:
                # Check if we already have this session running
                if not self.session_persistence.current_session_id:
                    success = self.ai_coach.start_session(track_name, car_name, load_previous=True)
                    if success:
                        self.current_session_active = True
                        logger.info(f"🏁 Auto-started session: {track_name} + {car_name}")
                
                # Only announce session start once per session
                if not self.session_start_announced:
                    # Send session start notification with reliable session info
                    session_data = {
                        "message": f"📊 Session started: {track_name}",
                        "category": "session",
                        "priority": 5,
                        "confidence": 100,
                        "session_info": {
                            "track_name": self.ai_coach.track_name,
                            "car_name": self.ai_coach.car_name,
                            "session_active": True,
                            "baseline_established": self.ai_coach.baseline_established
                        }
                    }
                    
                    logger.info(f"📊 Sending session start notification: {self.ai_coach.track_name} + {self.ai_coach.car_name}")
                    await self.broadcast_message(session_data)
                    self.session_start_announced = True  # Mark as announced
        
        except Exception as e:
            logger.error(f"Failed to auto-start session: {e}")

    def should_generate_coaching(self, telemetry_data):
        """Determine if we should generate coaching messages based on current conditions"""
        if not telemetry_data:
            logger.debug("❌ No telemetry data available for coaching")
            return False
        
        # Don't coach if car is in pits
        if telemetry_data.get('onPitRoad', False):
            logger.debug("❌ Car is in pits - not coaching")
            return False
        
        # Don't coach if car is stationary (speed very low)
        speed = telemetry_data.get('Speed', 0)  # Capital S for iRacing field
        if speed < 5:  # Less than 5 MPH
            logger.debug(f"❌ Speed too low ({speed:.1f} MPH) - not coaching")
            return False
        
        # Don't coach during caution/yellow flag conditions
        session_flags = telemetry_data.get('SessionFlags', 0)  # Capital S for iRacing field
        # Check for yellow flag conditions (caution)
        # iRacing session flags: yellow = 0x00100000 (bit 20)
        if session_flags & 0x00100000:  # Yellow flag
            logger.debug(f"❌ Yellow flag active (flags: 0x{session_flags:08x}) - not coaching")
            return False
        
        # Additional flag checks
        if session_flags & 0x00008000:  # Caution waving
            logger.debug(f"❌ Caution waving (flags: 0x{session_flags:08x}) - not coaching")
            return False
        
        if session_flags & 0x00010000:  # Caution
            logger.debug(f"❌ Caution active (flags: 0x{session_flags:08x}) - not coaching")
            return False
        
        # Don't coach if session is not active (practice, qualifying, race)
        session_state = telemetry_data.get('SessionState', 0)  # Capital S for iRacing field
        # SessionState: 0=invalid, 1=get_in_car, 2=warmup, 3=parade_laps, 4=racing, 5=checkered, 6=cool_down
        if session_state not in [2, 3, 4]:  # Only coach during warmup, parade laps, or racing
            logger.debug(f"❌ Invalid session state ({session_state}) - not coaching (need 2/3/4)")
            return False
        
        # Allow coaching on all track surfaces except not_in_world - we want to give feedback about off-track excursions!
        track_surface = telemetry_data.get('PlayerTrackSurface', 0)  # Capital P for iRacing field
        # TrackSurface: 0=not_in_world, 1=off_track, 2=in_pit_stall, 3=approaching_pits, 4=on_track
        if track_surface == 0:  # Only skip coaching when not in world (car not active)
            logger.debug(f"❌ Car not in world ({track_surface}) - not coaching")
            return False
        
        # Create descriptive track surface message for logging
        surface_names = {0: "not_in_world", 1: "off_track", 2: "in_pit_stall", 3: "approaching_pits", 4: "on_track"}
        surface_name = surface_names.get(track_surface, f"unknown({track_surface})")
        
        logger.info(f"✅ All coaching conditions met! Speed: {speed:.1f}, Session: {session_state}, Surface: {surface_name}, Flags: 0x{session_flags:08x}")
        return True

    async def handle_telemetry_connection(self, websocket, path=None):
        """Handle telemetry server connections"""
        logger.info("📡 Telemetry server connected")
        
        try:
            # Keep connection alive and process telemetry data
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    if data.get('type') == 'telemetry_data' and data.get('data'):
                        telemetry_data = data['data']
                        
                        # Cache the telemetry data
                        self.latest_telemetry = telemetry_data
                        
                        # Check for session changes periodically (every 2 seconds)
                        current_time = time.time()
                        if current_time - self.last_session_check_time > 2.0:
                            session_changed = self.detect_session_change(telemetry_data)
                            self.last_session_check_time = current_time
                        
                        # Try to auto-start session if needed
                        if not self.session_persistence.current_session_id:
                            await self._try_start_session(telemetry_data)
                        
                        # Process for coaching if session active
                        if self.session_persistence.current_session_id:
                            track_display_name = telemetry_data.get('TrackDisplayName', 'Unknown Track')  # Capital T for iRacing
                            track_name = telemetry_data.get('TrackName', track_display_name)  # Capital T for iRacing
                            car_name = telemetry_data.get('CarScreenName', telemetry_data.get('CarName', 'Unknown Car'))  # Capital C for iRacing
                            
                            logger.debug(f"🏁 Processing telemetry: {track_name} - {car_name}")
                            
                            # Check if enough time has passed since last message - REDUCED for more responsive coaching
                            current_time = time.time()
                            if current_time - self.last_message_time < 1.5:  # 1.5 second cooldown instead of 3
                                continue
                            
                            # Check if we should generate coaching
                            should_coach = self.should_generate_coaching(telemetry_data)
                            
                            if should_coach:
                                logger.info(f"🎯 ATTEMPTING TO GENERATE COACHING - Speed: {telemetry_data.get('Speed', 0):.1f}, Session: {telemetry_data.get('SessionState', 0)}")
                                
                                # Process telemetry through AI coach
                                coaching_messages = self.ai_coach.process_telemetry(telemetry_data)
                                
                                logger.info(f"🤖 AI Coach returned {len(coaching_messages) if coaching_messages else 0} messages")
                                
                                if coaching_messages and len(coaching_messages) > 0:
                                    for msg in coaching_messages:
                                        # Convert CoachingMessage object to dictionary format
                                        message_data = {
                                            "message": msg.message,
                                            "category": msg.category,
                                            "priority": msg.priority,
                                            "confidence": msg.confidence,
                                            "data_source": msg.data_source,
                                            "improvement_potential": getattr(msg, 'improvement_potential', 0.0)
                                        }
                                        
                                        await self.broadcast_message(message_data)
                                        logger.info(f"🤖 Sent coaching: {msg.message[:100]}...")
                                        
                                        # Save to persistence
                                        await self.session_persistence.save_message(
                                            self.session_persistence.current_session_id,
                                            msg.message,
                                            {"track": track_name, "car": car_name, "timestamp": current_time}
                                        )
                                    
                                    self.last_message_time = current_time
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from telemetry server")
                except Exception as e:
                    logger.error(f"Error processing telemetry: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("📡 Telemetry server disconnected")
        except Exception as e:
            logger.error(f"Telemetry connection error: {e}")

def main():
    """Main entry point"""
    # Check Python version for asyncio.run compatibility
    import sys
    if sys.version_info < (3, 7):
        logger.error("Python 3.7+ required for asyncio.run()")
        sys.exit(1)
    
    coaching_server = CoachingServer()
    
    async def run_server():
        """Async function to run the server"""
        try:
            logger.info("🚀 Starting GT3 AI Coaching Server...")
            
            # Start AI processing loop as a background task
            ai_task = asyncio.create_task(coaching_server.ai_processing_loop())
            
            # Coaching WebSocket server for UI clients
            coaching_server_task = websockets.serve(
                coaching_server.handle_coaching_client,
                "localhost",
                8082,
                ping_interval=20,
                ping_timeout=10,
                max_size=1048576  # 1MB max message size
            )
            
            # Telemetry WebSocket server for telemetry server connections
            telemetry_server_task = websockets.serve(
                coaching_server.handle_telemetry_connection,
                "localhost",
                8083,
                ping_interval=20,
                ping_timeout=10,
                max_size=1048576  # 1MB max message size
            )
            
            # Start both servers
            coaching_server_ws = await coaching_server_task
            telemetry_server_ws = await telemetry_server_task
            
            logger.info("🧠 GT3 AI Coaching Server running on ws://localhost:8082")
            logger.info("� Telemetry Server running on ws://localhost:8083")
            logger.info("�📊 Listening for telemetry data...")
            logger.info("Press Ctrl+C to stop")
            
            # Keep running until interrupted
            try:
                await asyncio.Future()  # Run forever
            except asyncio.CancelledError:
                logger.info("Server shutdown requested")
            finally:
                ai_task.cancel()
                coaching_server_ws.close()
                telemetry_server_ws.close()
                await coaching_server_ws.wait_closed()
                await telemetry_server_ws.wait_closed()
            
        except Exception as e:
            logger.error(f"Server error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    try:
        # Use asyncio.run() which handles event loop creation properly
        asyncio.run(run_server())
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down GT3 AI Coaching Server...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
