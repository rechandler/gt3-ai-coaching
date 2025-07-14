#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Example: Connecting Coaching Agent to Existing Telemetry System
Shows how to integrate the hybrid coaching agent with your existing telemetry server
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Any
import sys
import os

# Add coaching-agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from hybrid_coach import HybridCoachingAgent
from config import ConfigManager

logger = logging.getLogger(__name__)

class TelemetryCoachingBridge:
    """Bridge between telemetry server and coaching agent"""
    
    def __init__(self, coaching_config: Dict[str, Any]):
        self.coaching_agent = HybridCoachingAgent(coaching_config)
        self.is_running = False
        self.telemetry_connection = None
        
        # Message delivery callback (implement based on your UI system)
        self.message_callback = self.default_message_callback
        
    async def start(self):
        """Start the coaching bridge"""
        logger.info("Starting coaching bridge...")
        
        # Start the coaching agent
        await self.coaching_agent.start()
        self.is_running = True
        
        # Start telemetry connection
        await self.connect_to_telemetry()
        
    async def stop(self):
        """Stop the coaching bridge"""
        logger.info("Stopping coaching bridge...")
        self.is_running = False
        
        if self.coaching_agent:
            await self.coaching_agent.stop()
        
        if self.telemetry_connection:
            await self.telemetry_connection.close()
    
    async def connect_to_telemetry(self):
        """Connect to the existing telemetry server"""
        telemetry_url = "ws://localhost:8000/telemetry"  # Adjust to your telemetry server
        
        try:
            async with websockets.connect(telemetry_url) as websocket:
                self.telemetry_connection = websocket
                logger.info(f"Connected to telemetry server: {telemetry_url}")
                
                async for message in websocket:
                    if not self.is_running:
                        break
                    
                    try:
                        telemetry_data = json.loads(message)
                        await self.process_telemetry(telemetry_data)
                    except Exception as e:
                        logger.error(f"Error processing telemetry: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to connect to telemetry server: {e}")
    
    async def process_telemetry(self, telemetry_data: Dict[str, Any]):
        """Process telemetry through the coaching agent"""
        try:
            # Transform telemetry data if needed to match coaching agent format
            transformed_data = self.transform_telemetry(telemetry_data)
            
            # Process through coaching agent
            await self.coaching_agent.process_telemetry(transformed_data)
            
        except Exception as e:
            logger.error(f"Error in telemetry processing: {e}")
    
    def transform_telemetry(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw telemetry to coaching agent format"""
        # Map your telemetry fields to the standard format
        # Adjust these mappings based on your telemetry structure
        
        transformed = {}
        
        # Direct mappings
        field_mappings = {
            'Speed': 'speed',
            'Brake': 'brake_pct',
            'Throttle': 'throttle_pct',
            'SteeringWheelAngle': 'steering_angle',
            'LapDistPct': 'lap_distance_pct',
            'Gear': 'gear',
            'RPM': 'rpm',
            'LapCurrentLapTime': 'current_lap_time',
            'LapLastLapTime': 'last_lap_time'
        }
        
        for raw_key, standard_key in field_mappings.items():
            if raw_key in raw_telemetry:
                transformed[standard_key] = raw_telemetry[raw_key]
        
        # Calculated fields
        if 'LapDistPct' in raw_telemetry:
            transformed['lap_distance_pct'] = raw_telemetry['LapDistPct']
        
        # Convert brake and throttle to percentages if needed
        if 'brake_pct' in transformed and transformed['brake_pct'] > 1:
            transformed['brake_pct'] = transformed['brake_pct'] * 100
        
        if 'throttle_pct' in transformed and transformed['throttle_pct'] > 1:
            transformed['throttle_pct'] = transformed['throttle_pct'] * 100
        
        # Add session information
        if 'TrackName' in raw_telemetry:
            transformed['track_name'] = raw_telemetry['TrackName']
        if 'CarName' in raw_telemetry:
            transformed['car_name'] = raw_telemetry['CarName']
        if 'SessionType' in raw_telemetry:
            transformed['session_type'] = raw_telemetry['SessionType']
        
        # Add timestamp
        transformed['timestamp'] = asyncio.get_event_loop().time()
        
        return transformed
    
    def set_message_callback(self, callback):
        """Set callback for coaching message delivery"""
        self.message_callback = callback
    
    def default_message_callback(self, message: Dict[str, Any]):
        """Default message callback - just log the message"""
        logger.info(f"Coaching: {message.get('content', '')}")
    
    def get_coaching_stats(self) -> Dict[str, Any]:
        """Get coaching agent statistics"""
        if self.coaching_agent:
            return self.coaching_agent.get_stats()
        return {}

class WebSocketCoachingServer:
    """WebSocket server to deliver coaching messages to UI"""
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.clients = set()
        
    async def start_server(self):
        """Start the WebSocket server for coaching messages"""
        logger.info(f"Starting coaching WebSocket server on {self.host}:{self.port}")
        
        async def handle_client(websocket, path):
            self.clients.add(websocket)
            logger.info(f"Coaching client connected: {websocket.remote_address}")
            
            try:
                await websocket.wait_closed()
            finally:
                self.clients.remove(websocket)
                logger.info(f"Coaching client disconnected: {websocket.remote_address}")
        
        return await websockets.serve(handle_client, self.host, self.port)
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast coaching message to all connected clients"""
        if not self.clients:
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected

# Example usage
async def main():
    """Example integration with existing telemetry system"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load coaching configuration
    config_manager = ConfigManager()
    coaching_config = config_manager.get_config()
    
    # Create the bridge
    bridge = TelemetryCoachingBridge(coaching_config)
    
    # Create WebSocket server for coaching messages
    coaching_server = WebSocketCoachingServer()
    
    # Set up message delivery to WebSocket clients
    async def deliver_coaching_message(message: Dict[str, Any]):
        await coaching_server.broadcast_message(message)
    
    bridge.set_message_callback(deliver_coaching_message)
    
    try:
        # Start WebSocket server
        server = await coaching_server.start_server()
        
        # Start the coaching bridge
        await bridge.start()
        
        # Keep running until interrupted
        logger.info("Integration running... Press Ctrl+C to stop")
        await asyncio.Future()  # Run forever
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await bridge.stop()
        server.close()
        await server.wait_closed()

# Example of how to integrate with your existing telemetry processing
class ExistingTelemetryProcessor:
    """Example of how to modify your existing telemetry processor"""
    
    def __init__(self):
        # Your existing initialization
        self.coaching_bridge = None
        
    async def setup_coaching(self):
        """Setup coaching integration"""
        config_manager = ConfigManager()
        coaching_config = config_manager.get_config()
        
        self.coaching_bridge = TelemetryCoachingBridge(coaching_config)
        await self.coaching_bridge.start()
    
    async def process_telemetry_packet(self, telemetry_data: Dict[str, Any]):
        """Your existing telemetry processing with coaching integration"""
        
        # Your existing telemetry processing
        # ... existing code ...
        
        # Add coaching processing
        if self.coaching_bridge:
            await self.coaching_bridge.process_telemetry(telemetry_data)
        
        # Your existing code continues...

# Configuration example for different telemetry sources
TELEMETRY_SOURCE_CONFIGS = {
    'iracing': {
        'field_mappings': {
            'Speed': 'speed',
            'Brake': 'brake_pct',
            'Throttle': 'throttle_pct',
            'SteeringWheelAngle': 'steering_angle',
            'LapDistPct': 'lap_distance_pct'
        },
        'scale_factors': {
            'brake_pct': 100,  # Convert 0-1 to 0-100
            'throttle_pct': 100
        }
    },
    'custom_simulator': {
        'field_mappings': {
            'car_speed': 'speed',
            'brake_input': 'brake_pct',
            'throttle_input': 'throttle_pct',
            'wheel_angle': 'steering_angle',
            'track_position': 'lap_distance_pct'
        },
        'scale_factors': {}
    }
}

if __name__ == "__main__":
    asyncio.run(main())
