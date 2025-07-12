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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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
        
        # Message queue and history
        self.message_queue = []
        self.last_message_id = 0
        
        # Telemetry data cache (received from telemetry server)
        self.latest_telemetry = None
        self.telemetry_updated = False
        
        logger.info("🧠 GT3 AI Coaching Server initialized")
    
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
    
    async def broadcast_message(self, message_data):
        """Broadcast coaching message to all connected clients"""
        if not self.clients:
            return
        
        # Create message with unique ID
        self.last_message_id += 1
        coaching_message = {
            "type": "coaching",
            "id": self.last_message_id,
            "timestamp": time.time(),
            "data": message_data
        }
        
        # Add to queue (keep last 50 messages)
        self.message_queue.append(coaching_message)
        if len(self.message_queue) > 50:
            self.message_queue.pop(0)
        
        # Broadcast to all clients
        disconnected_clients = set()
        message_json = json.dumps(coaching_message)
        
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
        
        logger.info(f"📢 Broadcasted coaching message to {len(self.clients)} clients: {message_data.get('message', '')[:50]}...")
    
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
        """Main AI processing loop - processes telemetry and generates coaching"""
        from ai_coach import LocalAICoach
        
        ai_coach = LocalAICoach()
        last_coaching_message = None
        last_message_time = 0
        min_message_interval = 3.0  # Minimum 3 seconds between messages
        
        # Connect to telemetry server to receive data
        telemetry_ws = None
        
        logger.info("🤖 AI processing loop started")
        
        while True:
            try:
                # Connect to telemetry server if not connected
                if telemetry_ws is None:
                    try:
                        import websockets
                        telemetry_ws = await websockets.connect("ws://localhost:8081")
                        logger.info("📊 Connected to telemetry server")
                    except Exception as e:
                        logger.debug(f"Could not connect to telemetry server: {e}")
                        await asyncio.sleep(5)
                        continue
                
                # Try to receive telemetry data
                try:
                    # Set a timeout for receiving data
                    message = await asyncio.wait_for(telemetry_ws.recv(), timeout=5.0)
                    
                    try:
                        data = json.loads(message)
                        
                        if data.get('type') == 'Telemetry' and data.get('data'):
                            telemetry_data = data['data']
                            
                            # Check if we should process coaching (car is actually moving/racing)
                            should_coach = self.should_generate_coaching(telemetry_data)
                            
                            if should_coach:
                                # Process telemetry through AI coach
                                coaching_messages = ai_coach.process_telemetry(telemetry_data)
                                
                                if coaching_messages:
                                    primary_message = coaching_messages[0]
                                    current_time = time.time()
                                    
                                    # Only send if message has changed AND enough time has passed
                                    if (primary_message.message != last_coaching_message and 
                                        current_time - last_message_time >= min_message_interval):
                                        
                                        # Prepare coaching data
                                        coaching_data = {
                                            "message": primary_message.message,
                                            "category": primary_message.category,
                                            "priority": primary_message.priority,
                                            "confidence": int(primary_message.confidence)
                                        }
                                        
                                        # Add secondary messages if any
                                        if len(coaching_messages) > 1:
                                            coaching_data["secondary_messages"] = [
                                                {
                                                    "message": msg.message,
                                                    "category": msg.category,
                                                    "priority": msg.priority,
                                                    "confidence": int(msg.confidence)
                                                }
                                                for msg in coaching_messages[1:6]  # Max 5 secondary
                                            ]
                                        
                                        # Add improvement potential if available
                                        if hasattr(primary_message, 'improvement_potential') and primary_message.improvement_potential > 0:
                                            coaching_data["improvement_potential"] = primary_message.improvement_potential
                                        
                                        # Broadcast the coaching message
                                        await self.broadcast_message(coaching_data)
                                        last_coaching_message = primary_message.message
                                        last_message_time = current_time
                            else:
                                # Reset last message when not coaching so we can restart properly
                                if last_coaching_message is not None:
                                    logger.debug("🛑 Car not in racing condition, stopping coaching")
                                    last_coaching_message = None
                    
                    except json.JSONDecodeError:
                        logger.debug("Received non-JSON data from telemetry server")
                    
                except asyncio.TimeoutError:
                    # No data received, continue loop
                    pass
                except websockets.exceptions.ConnectionClosed:
                    logger.info("📊 Telemetry server connection closed")
                    telemetry_ws = None
                    await asyncio.sleep(2)
                except Exception as recv_error:
                    logger.debug(f"Error receiving from telemetry server: {recv_error}")
                    telemetry_ws = None
                    await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in AI processing loop: {e}")
                telemetry_ws = None
                await asyncio.sleep(1)

    def should_generate_coaching(self, telemetry_data):
        """Determine if we should generate coaching messages based on current conditions"""
        if not telemetry_data:
            return False
        
        # Don't coach if car is in pits
        if telemetry_data.get('onPitRoad', False):
            return False
        
        # Don't coach if car is stationary (speed very low)
        speed = telemetry_data.get('speed', 0)
        if speed < 5:  # Less than 5 MPH
            return False
        
        # Don't coach during caution/yellow flag conditions
        session_flags = telemetry_data.get('sessionFlags', 0)
        # Check for yellow flag conditions (caution)
        # iRacing session flags: yellow = 0x00100000 (bit 20)
        if session_flags & 0x00100000:  # Yellow flag
            return False
        
        # Additional flag checks
        if session_flags & 0x00008000:  # Caution waving
            return False
        
        if session_flags & 0x00010000:  # Caution
            return False
        
        # Don't coach if session is not active (practice, qualifying, race)
        session_state = telemetry_data.get('sessionState', 0)
        # SessionState: 0=invalid, 1=get_in_car, 2=warmup, 3=parade_laps, 4=racing, 5=checkered, 6=cool_down
        if session_state not in [2, 3, 4]:  # Only coach during warmup, parade laps, or racing
            return False
        
        # Don't coach if car is not on track surface
        track_surface = telemetry_data.get('playerTrackSurface', 0)
        # TrackSurface: 0=not_in_world, 1=off_track, 2=in_pit_stall, 3=approaching_pits, 4=on_track
        if track_surface != 4:  # Only coach when on track
            return False
        
        return True

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
            server = await websockets.serve(
                coaching_server.handle_coaching_client,
                "localhost",
                8082,
                ping_interval=20,
                ping_timeout=10,
                max_size=1048576  # 1MB max message size
            )
            
            logger.info("🧠 GT3 AI Coaching Server running on ws://localhost:8082")
            logger.info("📊 Listening for telemetry data...")
            logger.info("Press Ctrl+C to stop")
            
            # Keep running until interrupted
            try:
                await asyncio.Future()  # Run forever
            except asyncio.CancelledError:
                logger.info("Server shutdown requested")
            finally:
                ai_task.cancel()
                server.close()
                await server.wait_closed()
            
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
