#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coaching System Schemas
=======================

Comprehensive Pydantic models for type safety, validation, and maintainability.
These schemas define explicit data interfaces for all coaching system components.

Features:
- Type-safe data validation
- Automatic serialization/deserialization
- Schema evolution support
- API documentation generation
- Runtime validation
"""

from typing import Dict, List, Optional, Any, Union, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
import time

# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class MessagePriority(str, Enum):
    """Message priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class CoachingMode(str, Enum):
    """Coaching modes"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    RACE = "race"

class ReferenceType(str, Enum):
    """Reference lap types"""
    PERSONAL_BEST = "personal_best"
    SESSION_BEST = "session_best"
    OPTIMAL = "optimal"
    CONSISTENCY = "consistency"
    RACE_PACE = "race_pace"
    ENGINEER = "engineer"

class EventType(str, Enum):
    """Event types for coaching system"""
    LAP_COMPLETED = "lap_completed"
    SECTOR_COMPLETED = "sector_completed"
    PERSONAL_BEST = "personal_best"
    SECTOR_BEST = "sector_best"
    MISTAKE_DETECTED = "mistake_detected"
    COACHING_MESSAGE = "coaching_message"
    PERFORMANCE_UPDATE = "performance_update"
    SESSION_START = "session_start"
    SESSION_END = "session_end"

class InsightType(str, Enum):
    """Insight types for coaching analysis"""
    CORNER_ANALYSIS = "corner_analysis"
    SECTOR_ANALYSIS = "sector_analysis"
    LAP_ANALYSIS = "lap_analysis"
    MISTAKE_ANALYSIS = "mistake_analysis"
    PERFORMANCE_TREND = "performance_trend"
    RACING_LINE = "racing_line"
    BRAKING_TECHNIQUE = "braking_technique"
    THROTTLE_TECHNIQUE = "throttle_technique"

# =============================================================================
# TELEMETRY SCHEMAS
# =============================================================================

class TelemetryData(BaseModel):
    """Telemetry data from iRacing"""
    timestamp: float = Field(..., description="Unix timestamp")
    lap: Optional[int] = Field(None, description="Current lap number")
    lapDistPct: Optional[float] = Field(None, ge=0.0, le=1.0, description="Lap distance percentage")
    speed: Optional[float] = Field(None, ge=0.0, description="Speed in km/h")
    throttle: Optional[float] = Field(None, ge=0.0, le=100.0, description="Throttle percentage")
    brake: Optional[float] = Field(None, ge=0.0, le=100.0, description="Brake percentage")
    steering: Optional[float] = Field(None, description="Steering angle")
    gear: Optional[int] = Field(None, ge=0, description="Current gear")
    rpm: Optional[float] = Field(None, ge=0.0, description="Engine RPM")
    track_name: Optional[str] = Field(None, description="Track name")
    car_name: Optional[str] = Field(None, description="Car name")
    session_type: Optional[str] = Field(None, description="Session type")
    lapCurrentLapTime: Optional[float] = Field(None, ge=0.0, description="Current lap time")
    lapLastLapTime: Optional[float] = Field(None, ge=0.0, description="Last lap time")
    lapBestLapTime: Optional[float] = Field(None, ge=0.0, description="Best lap time")
    fuel_level: Optional[float] = Field(None, ge=0.0, description="Fuel level")
    tire_pressure_fl: Optional[float] = Field(None, description="Front left tire pressure")
    tire_pressure_fr: Optional[float] = Field(None, description="Front right tire pressure")
    tire_pressure_rl: Optional[float] = Field(None, description="Rear left tire pressure")
    tire_pressure_rr: Optional[float] = Field(None, description="Rear right tire pressure")
    on_pit_road: Optional[bool] = Field(None, description="Whether on pit road")
    lapCompleted: Optional[bool] = Field(None, description="Lap completion flag")
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        if v <= 0:
            raise ValueError('Timestamp must be positive')
        return v
    
    @validator('lapDistPct')
    def validate_lap_dist_pct(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError('Lap distance percentage must be between 0.0 and 1.0')
        return v

class SectorData(BaseModel):
    """Sector telemetry and timing data"""
    sector_number: int = Field(..., ge=0, description="Sector number (0-based)")
    sector_time: float = Field(..., ge=0.0, description="Sector time in seconds")
    telemetry_points: List[TelemetryData] = Field(default_factory=list, description="Telemetry points in sector")
    entry_speed: float = Field(..., ge=0.0, description="Entry speed in km/h")
    exit_speed: float = Field(..., ge=0.0, description="Exit speed in km/h")
    min_speed: float = Field(..., ge=0.0, description="Minimum speed in sector")
    max_speed: float = Field(..., ge=0.0, description="Maximum speed in sector")
    avg_throttle: float = Field(..., ge=0.0, le=100.0, description="Average throttle percentage")
    avg_brake: float = Field(..., ge=0.0, le=100.0, description="Average brake percentage")
    max_steering: float = Field(..., description="Maximum steering angle")
    start_pct: float = Field(..., ge=0.0, le=1.0, description="Sector start percentage")
    end_pct: float = Field(..., ge=0.0, le=1.0, description="Sector end percentage")
    
    @validator('end_pct')
    def validate_end_pct(cls, v, values):
        if 'start_pct' in values and v <= values['start_pct']:
            raise ValueError('End percentage must be greater than start percentage')
        return v

# =============================================================================
# LAP AND SECTOR SCHEMAS
# =============================================================================

class LapData(BaseModel):
    """Complete lap telemetry data"""
    lap_number: int = Field(..., ge=1, description="Lap number")
    lap_time: float = Field(..., ge=0.0, description="Lap time in seconds")
    sector_times: List[float] = Field(..., description="Sector times in seconds")
    telemetry_points: List[TelemetryData] = Field(..., description="All telemetry points in lap")
    track_name: str = Field(..., description="Track name")
    car_name: str = Field(..., description="Car name")
    timestamp: float = Field(..., description="Lap completion timestamp")
    is_valid: bool = Field(default=True, description="Whether lap is valid")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('sector_times')
    def validate_sector_times(cls, v):
        if not v:
            raise ValueError('Sector times cannot be empty')
        if any(t < 0 for t in v):
            raise ValueError('Sector times must be positive')
        return v
    
    @validator('lap_time')
    def validate_lap_time(cls, v):
        if v <= 0:
            raise ValueError('Lap time must be positive')
        return v

class ReferenceLap(BaseModel):
    """Reference lap for comparison"""
    lap_data: LapData = Field(..., description="Lap data")
    reference_type: ReferenceType = Field(..., description="Type of reference")
    created_at: float = Field(..., description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('created_at')
    def validate_created_at(cls, v):
        if v <= 0:
            raise ValueError('Creation timestamp must be positive')
        return v

# =============================================================================
# EVENT SCHEMAS
# =============================================================================

class BaseEvent(BaseModel):
    """Base event schema"""
    event_type: EventType = Field(..., description="Type of event")
    timestamp: float = Field(..., description="Event timestamp")
    session_id: Optional[str] = Field(None, description="Session identifier")
    track_name: Optional[str] = Field(None, description="Track name")
    car_name: Optional[str] = Field(None, description="Car name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class LapCompletedEvent(BaseEvent):
    """Lap completion event"""
    event_type: Literal[EventType.LAP_COMPLETED] = EventType.LAP_COMPLETED
    lap_data: LapData = Field(..., description="Completed lap data")
    is_personal_best: bool = Field(..., description="Whether this is a personal best")
    is_session_best: bool = Field(..., description="Whether this is a session best")
    delta_to_pb: Optional[float] = Field(None, description="Delta to personal best")
    delta_to_sb: Optional[float] = Field(None, description="Delta to session best")

class SectorCompletedEvent(BaseEvent):
    """Sector completion event"""
    event_type: Literal[EventType.SECTOR_COMPLETED] = EventType.SECTOR_COMPLETED
    sector_data: SectorData = Field(..., description="Completed sector data")
    is_best_sector: bool = Field(..., description="Whether this is a best sector")
    is_session_best_sector: bool = Field(..., description="Whether this is a session best sector")
    delta_to_best: Optional[float] = Field(None, description="Delta to best sector")

class PersonalBestEvent(BaseEvent):
    """Personal best achievement event"""
    event_type: Literal[EventType.PERSONAL_BEST] = EventType.PERSONAL_BEST
    lap_data: LapData = Field(..., description="Personal best lap data")
    improvement: float = Field(..., description="Improvement over previous best")
    previous_best: float = Field(..., description="Previous best lap time")

class SectorBestEvent(BaseEvent):
    """Sector best achievement event"""
    event_type: Literal[EventType.SECTOR_BEST] = EventType.SECTOR_BEST
    sector_data: SectorData = Field(..., description="Sector best data")
    sector_number: int = Field(..., description="Sector number")
    improvement: float = Field(..., description="Improvement over previous best")
    previous_best: float = Field(..., description="Previous best sector time")

class MistakeDetectedEvent(BaseEvent):
    """Mistake detection event"""
    event_type: Literal[EventType.MISTAKE_DETECTED] = EventType.MISTAKE_DETECTED
    mistake_type: str = Field(..., description="Type of mistake")
    severity: float = Field(..., ge=0.0, le=1.0, description="Mistake severity")
    time_loss: float = Field(..., ge=0.0, description="Estimated time loss")
    corner_name: Optional[str] = Field(None, description="Corner where mistake occurred")
    description: str = Field(..., description="Mistake description")
    telemetry_snapshot: Optional[TelemetryData] = Field(None, description="Telemetry at mistake")

# =============================================================================
# COACHING MESSAGE SCHEMAS
# =============================================================================

class CoachingMessage(BaseModel):
    """Coaching message with metadata"""
    content: str = Field(..., min_length=1, description="Message content")
    category: str = Field(..., description="Message category")
    priority: MessagePriority = Field(..., description="Message priority")
    source: str = Field(..., description="Message source")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")
    context: str = Field(..., description="Message context")
    timestamp: float = Field(..., description="Message timestamp")
    delivered: bool = Field(default=False, description="Whether message was delivered")
    attempts: int = Field(default=0, ge=0, description="Delivery attempts")
    
    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class CoachingInsight(BaseModel):
    """Coaching insight with analysis data"""
    insight_type: InsightType = Field(..., description="Type of insight")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")
    severity: float = Field(..., ge=0.0, le=1.0, description="Severity level")
    data: Dict[str, Any] = Field(..., description="Insight data")
    telemetry_context: Optional[TelemetryData] = Field(None, description="Relevant telemetry")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    timestamp: float = Field(..., description="Insight timestamp")

# =============================================================================
# PERFORMANCE SCHEMAS
# =============================================================================

class PerformanceMetrics(BaseModel):
    """Performance metrics for analysis"""
    lap_time: float = Field(..., ge=0.0, description="Lap time")
    sector_times: List[float] = Field(..., description="Sector times")
    avg_speed: float = Field(..., ge=0.0, description="Average speed")
    max_speed: float = Field(..., ge=0.0, description="Maximum speed")
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="Consistency score")
    throttle_usage: float = Field(..., ge=0.0, le=100.0, description="Throttle usage percentage")
    brake_usage: float = Field(..., ge=0.0, le=100.0, description="Brake usage percentage")
    racing_line_score: float = Field(..., ge=0.0, le=1.0, description="Racing line adherence")
    mistakes_count: int = Field(..., ge=0, description="Number of mistakes")
    total_time_loss: float = Field(..., ge=0.0, description="Total time loss from mistakes")

class RollingStintAnalysis(BaseModel):
    """Rolling stint performance analysis"""
    total_laps: int = Field(..., ge=0, description="Total laps in stint")
    stint_duration: float = Field(..., ge=0.0, description="Stint duration in seconds")
    avg_lap_time: float = Field(..., ge=0.0, description="Average lap time")
    best_lap_time: float = Field(..., ge=0.0, description="Best lap time in stint")
    worst_lap_time: float = Field(..., ge=0.0, description="Worst lap time in stint")
    lap_time_consistency: float = Field(..., ge=0.0, description="Lap time consistency (std dev)")
    recent_avg: float = Field(..., ge=0.0, description="Recent average lap time")
    trend: str = Field(..., description="Performance trend")
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="Consistency score")

class SessionSummary(BaseModel):
    """Comprehensive session summary"""
    session_id: str = Field(..., description="Session identifier")
    session_start: float = Field(..., description="Session start timestamp")
    session_end: Optional[float] = Field(None, description="Session end timestamp")
    total_laps: int = Field(..., ge=0, description="Total laps completed")
    session_best_lap: Optional[float] = Field(None, ge=0.0, description="Session best lap time")
    personal_best_lap: Optional[float] = Field(None, ge=0.0, description="Personal best lap time")
    avg_lap_time: float = Field(..., ge=0.0, description="Average lap time")
    lap_time_consistency: float = Field(..., ge=0.0, description="Lap time consistency")
    best_sector_times: List[float] = Field(default_factory=list, description="Best sector times")
    session_sector_bests: List[float] = Field(default_factory=list, description="Session sector bests")
    track_name: str = Field(..., description="Track name")
    car_name: str = Field(..., description="Car name")
    coaching_mode: CoachingMode = Field(..., description="Coaching mode used")
    total_mistakes: int = Field(..., ge=0, description="Total mistakes detected")
    total_time_lost: float = Field(..., ge=0.0, description="Total time lost to mistakes")
    session_score: float = Field(..., ge=0.0, le=100.0, description="Overall session score")

# =============================================================================
# REFERENCE COMPARISON SCHEMAS
# =============================================================================

class ReferenceComparison(BaseModel):
    """Reference lap comparison data"""
    reference_type: ReferenceType = Field(..., description="Type of reference")
    reference_lap_time: float = Field(..., ge=0.0, description="Reference lap time")
    current_elapsed: float = Field(..., ge=0.0, description="Current elapsed time")
    delta_to_reference: float = Field(..., description="Delta to reference")
    is_ahead: bool = Field(..., description="Whether ahead of reference")
    sector_deltas: List[float] = Field(..., description="Sector-by-sector deltas")
    reference_lap_data: LapData = Field(..., description="Reference lap data")
    
    @validator('sector_deltas')
    def validate_sector_deltas(cls, v):
        if not v:
            raise ValueError('Sector deltas cannot be empty')
        return v

class SectorComparison(BaseModel):
    """Sector-by-sector comparison"""
    sector: int = Field(..., ge=1, description="Sector number")
    reference_time: float = Field(..., ge=0.0, description="Reference sector time")
    current_time: float = Field(..., ge=0.0, description="Current sector time")
    delta: float = Field(..., description="Time delta")
    is_faster: bool = Field(..., description="Whether current time is faster")

# =============================================================================
# API REQUEST/RESPONSE SCHEMAS
# =============================================================================

class CoachingRequest(BaseModel):
    """Request for coaching analysis"""
    telemetry_data: TelemetryData = Field(..., description="Current telemetry data")
    session_context: Optional[Dict[str, Any]] = Field(None, description="Session context")
    coaching_mode: CoachingMode = Field(default=CoachingMode.INTERMEDIATE, description="Coaching mode")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")

class CoachingResponse(BaseModel):
    """Response with coaching insights"""
    insights: List[CoachingInsight] = Field(..., description="Generated insights")
    messages: List[CoachingMessage] = Field(..., description="Coaching messages")
    performance_metrics: Optional[PerformanceMetrics] = Field(None, description="Performance metrics")
    reference_comparison: Optional[ReferenceComparison] = Field(None, description="Reference comparison")
    timestamp: float = Field(..., description="Response timestamp")

class SessionStartRequest(BaseModel):
    """Session start request"""
    track_name: str = Field(..., description="Track name")
    car_name: str = Field(..., description="Car name")
    session_type: str = Field(..., description="Session type")
    coaching_mode: CoachingMode = Field(..., description="Coaching mode")
    user_id: Optional[str] = Field(None, description="User identifier")

class SessionEndRequest(BaseModel):
    """Session end request"""
    session_id: str = Field(..., description="Session identifier")
    final_telemetry: Optional[TelemetryData] = Field(None, description="Final telemetry")
    session_notes: Optional[str] = Field(None, description="Session notes")

# =============================================================================
# CONFIGURATION SCHEMAS
# =============================================================================

class CoachingConfig(BaseModel):
    """Coaching system configuration"""
    coaching_mode: CoachingMode = Field(default=CoachingMode.INTERMEDIATE, description="Default coaching mode")
    message_rate_limit: int = Field(default=5, ge=1, description="Messages per minute limit")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Confidence threshold")
    severity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Severity threshold")
    enable_ai_coaching: bool = Field(default=True, description="Enable AI coaching")
    enable_local_coaching: bool = Field(default=True, description="Enable local coaching")
    reference_persistence: bool = Field(default=True, description="Enable reference persistence")
    debug_mode: bool = Field(default=False, description="Enable debug mode")

class TrackConfig(BaseModel):
    """Track-specific configuration"""
    track_name: str = Field(..., description="Track name")
    sector_boundaries: List[float] = Field(..., description="Sector boundaries")
    reference_laps: Dict[ReferenceType, ReferenceLap] = Field(default_factory=dict, description="Reference laps")
    coaching_focus: List[str] = Field(default_factory=list, description="Coaching focus areas")
    difficulty_level: str = Field(default="intermediate", description="Track difficulty")

# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_telemetry_data(data: Dict[str, Any]) -> TelemetryData:
    """Validate and create TelemetryData from dictionary"""
    return TelemetryData(**data)

def validate_lap_data(data: Dict[str, Any]) -> LapData:
    """Validate and create LapData from dictionary"""
    return LapData(**data)

def validate_coaching_message(data: Dict[str, Any]) -> CoachingMessage:
    """Validate and create CoachingMessage from dictionary"""
    return CoachingMessage(**data)

def validate_event_data(data: Dict[str, Any]) -> BaseEvent:
    """Validate and create appropriate event from dictionary"""
    event_type = data.get('event_type')
    if event_type == EventType.LAP_COMPLETED:
        return LapCompletedEvent(**data)
    elif event_type == EventType.SECTOR_COMPLETED:
        return SectorCompletedEvent(**data)
    elif event_type == EventType.PERSONAL_BEST:
        return PersonalBestEvent(**data)
    elif event_type == EventType.SECTOR_BEST:
        return SectorBestEvent(**data)
    elif event_type == EventType.MISTAKE_DETECTED:
        return MistakeDetectedEvent(**data)
    else:
        return BaseEvent(**data)

# =============================================================================
# SERIALIZATION UTILITIES
# =============================================================================

def serialize_event(event: BaseEvent) -> Dict[str, Any]:
    """Serialize event to dictionary"""
    return event.dict()

def deserialize_event(data: Dict[str, Any]) -> BaseEvent:
    """Deserialize event from dictionary"""
    return validate_event_data(data)

def serialize_telemetry(telemetry: TelemetryData) -> Dict[str, Any]:
    """Serialize telemetry to dictionary"""
    return telemetry.dict()

def deserialize_telemetry(data: Dict[str, Any]) -> TelemetryData:
    """Deserialize telemetry from dictionary"""
    return validate_telemetry_data(data) 