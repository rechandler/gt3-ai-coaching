#!/usr/bin/env python3
"""
Test LLM Integration for Track Metadata
=======================================

Demonstrates the LLM-powered track metadata generation.
"""

import asyncio
import logging
import os
from typing import Dict, Any

from track_metadata_manager import TrackMetadataManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_llm_track_generation():
    """Test LLM generation of track metadata"""
    logger.info("🧪 Testing LLM track metadata generation...")
    
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning("⚠️ No OPENAI_API_KEY found in environment")
        logger.info("💡 Set OPENAI_API_KEY to test LLM generation")
        return
    
    # Initialize track metadata manager
    track_manager = TrackMetadataManager()
    
    # Test tracks that aren't in the default cache
    test_tracks = [
        "Silverstone",
        "Mount Panorama",
        "Interlagos",
        "Suzuka"
    ]
    
    for track_name in test_tracks:
        logger.info(f"🔍 Testing LLM generation for: {track_name}")
        
        try:
            # Try to get metadata (should trigger LLM generation)
            segments = await track_manager.get_track_metadata(track_name)
            
            if segments:
                logger.info(f"✅ Successfully generated {len(segments)} segments for {track_name}")
                
                # Show first few segments
                for i, segment in enumerate(segments[:3]):
                    logger.info(f"   {i+1}. {segment['name']} ({segment['type']}) - {segment['description']}")
                
                if len(segments) > 3:
                    logger.info(f"   ... and {len(segments) - 3} more segments")
            else:
                logger.warning(f"⚠️ No segments generated for {track_name}")
                
        except Exception as e:
            logger.error(f"❌ Error generating metadata for {track_name}: {e}")
        
        # Small delay between requests
        await asyncio.sleep(1)
    
    # Show available tracks
    available_tracks = track_manager.get_available_tracks()
    logger.info(f"📁 Total available tracks: {len(available_tracks)}")
    logger.info(f"📁 Available tracks: {available_tracks}")

async def test_hybrid_approach():
    """Test the hybrid approach (Firebase -> Local -> LLM)"""
    logger.info("🧪 Testing hybrid approach...")
    
    track_manager = TrackMetadataManager()
    
    # Test with a track that should be in local cache
    local_track = "Spa-Francorchamps"
    logger.info(f"🔍 Testing local cache for: {local_track}")
    
    segments = await track_manager.get_track_metadata(local_track)
    if segments:
        logger.info(f"✅ Found {len(segments)} segments in local cache for {local_track}")
    else:
        logger.warning(f"⚠️ No segments found for {local_track}")
    
    # Test with a new track (should trigger LLM)
    new_track = "Fuji Speedway"
    logger.info(f"🔍 Testing LLM generation for: {new_track}")
    
    segments = await track_manager.get_track_metadata(new_track)
    if segments:
        logger.info(f"✅ Generated {len(segments)} segments for {new_track}")
    else:
        logger.warning(f"⚠️ No segments generated for {new_track}")

async def main():
    """Main test function"""
    try:
        # Test hybrid approach first
        await test_hybrid_approach()
        
        # Test LLM generation
        await test_llm_track_generation()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 