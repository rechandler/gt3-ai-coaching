"""
GT3 AI Coaching - Telemetry Server Services

This package contains the modular services that make up the GT3 AI coaching telemetry server.

Services:
- TelemetryService: Direct interface to iRacing SDK
- CoachingDataService: Process telemetry and manage coaching sessions
- ServiceLauncher: Coordinate all services
"""

from .telemetry_service import TelemetryService
from .coaching_data_service import CoachingDataService
from .launcher import ServiceLauncher

__all__ = ['TelemetryService', 'CoachingDataService', 'ServiceLauncher']
