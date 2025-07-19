"""
GT3 AI Coaching - Telemetry Server Services

This package contains the modular services that make up the GT3 AI coaching telemetry server.

Services:
- TelemetryService: Direct interface to iRacing SDK
- CoachingDataService: Process telemetry and manage coaching sessions
"""

from .telemetry_service import TelemetryService

__all__ = ['TelemetryService']
