import logging
from typing import Dict, Any, List, Optional
import asyncio
import json

logger = logging.getLogger(__name__)

class TrackMetadataManager:
    """
    Handles LLM-powered enrichment of track metadata (segments, turns, etc.)
    and maps telemetry lap percentage to track segments/turns.
    """
    def __init__(self, remote_ai_coach):
        self.remote_ai_coach = remote_ai_coach
        self.current_track_name: Optional[str] = None
        self.track_metadata: Optional[List[Dict[str, Any]]] = None
        self._metadata_cache: Dict[str, List[Dict[str, Any]]] = {}

    async def ensure_metadata_for_track(self, track_name: str, context: Any = None):
        """
        Ensure metadata for the given track is loaded (query LLM if needed).
        """
        if not track_name:
            return
        if track_name == self.current_track_name and self.track_metadata:
            return  # Already loaded
        if track_name in self._metadata_cache:
            self.current_track_name = track_name
            self.track_metadata = self._metadata_cache[track_name]
            return
        # Query LLM for track breakdown
        logger.info(f"Querying LLM for metadata for track: {track_name}")
        prompt = (
            f"Provide a JSON array breakdown of the '{track_name}' racing circuit. "
            "For each segment or turn, include: 'name', 'number' (if any), and "
            "'lap_percentage_range' (as [start, end] in percent, e.g., [12, 15]). "
            "If possible, use official turn names/numbers. Example output: "
            "[{'name': 'Turn 1', 'number': 1, 'lap_percentage_range': [2, 4]}, ...]"
        )
        # Use the remote AI coach to get the response
        ai_response = await self.remote_ai_coach.generate_coaching(
            {'situation': 'track_metadata_request', 'confidence': 1.0, 'data': {'track_name': track_name}},
            {},
            context
        )
        if not ai_response or not ai_response.get('message'):
            logger.warning(f"No metadata received from LLM for track: {track_name}")
            return
        try:
            # Try to extract JSON from the response
            metadata = self._extract_json(ai_response['message'])
            if metadata:
                self._metadata_cache[track_name] = metadata
                self.current_track_name = track_name
                self.track_metadata = metadata
                logger.info(f"Loaded metadata for track: {track_name}")
            else:
                logger.warning(f"Failed to parse metadata JSON for track: {track_name}")
        except Exception as e:
            logger.error(f"Error parsing LLM metadata for track: {track_name}: {e}")

    def get_current_segment(self, lap_distance_pct: float) -> Optional[Dict[str, Any]]:
        """
        Given the current lap percentage, return the segment/turn dict.
        """
        if not self.track_metadata:
            return None
        lap_pct = lap_distance_pct * 100  # Convert to percent
        for segment in self.track_metadata:
            rng = segment.get('lap_percentage_range')
            if rng and rng[0] <= lap_pct <= rng[1]:
                return segment
        return None

    @staticmethod
    def _extract_json(text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract the first JSON array found in the text.
        """
        try:
            # Find the first '[' and last ']' to extract the JSON array
            start = text.find('[')
            end = text.rfind(']')
            if start != -1 and end != -1 and end > start:
                json_str = text[start:end+1]
                return json.loads(json_str)
        except Exception:
            pass
        return None 