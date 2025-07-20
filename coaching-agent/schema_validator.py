#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema Validation Utilities
==========================

Robust validation and error handling for coaching system data structures.
Provides type-safe validation, error reporting, and data transformation utilities.

Features:
- Comprehensive error handling
- Detailed validation error messages
- Data transformation utilities
- Schema evolution support
- Performance monitoring
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from pydantic import ValidationError, BaseModel
from schemas import (
    TelemetryData, LapData, SectorData, ReferenceLap, ReferenceType,
    CoachingMessage, CoachingInsight, BaseEvent, EventType,
    validate_telemetry_data, validate_lap_data, validate_coaching_message,
    validate_event_data
)

logger = logging.getLogger(__name__)

class ValidationResult:
    """Result of a validation operation"""
    
    def __init__(self, is_valid: bool, data: Optional[Any] = None, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.data = data
        self.errors = errors or []
        self.timestamp = time.time()
    
    def __bool__(self):
        return self.is_valid
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
        self.is_valid = False

class SchemaValidator:
    """Comprehensive schema validation utility"""
    
    def __init__(self):
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'validation_errors': {}
        }
    
    def validate_telemetry(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate telemetry data with detailed error reporting"""
        try:
            self.validation_stats['total_validations'] += 1
            telemetry = TelemetryData(**data)
            self.validation_stats['successful_validations'] += 1
            return ValidationResult(True, telemetry)
        except ValidationError as e:
            self.validation_stats['failed_validations'] += 1
            errors = [f"{error['loc'][0] if error['loc'] else 'unknown'}: {error['msg']}" for error in e.errors()]
            self.validation_stats['validation_errors']['telemetry'] = errors
            logger.warning(f"Telemetry validation failed: {errors}")
            return ValidationResult(False, None, errors)
        except Exception as e:
            self.validation_stats['failed_validations'] += 1
            error_msg = f"Unexpected error during telemetry validation: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(False, None, [error_msg])
    
    def validate_lap_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate lap data with detailed error reporting"""
        try:
            self.validation_stats['total_validations'] += 1
            lap_data = LapData(**data)
            self.validation_stats['successful_validations'] += 1
            return ValidationResult(True, lap_data)
        except ValidationError as e:
            self.validation_stats['failed_validations'] += 1
            errors = [f"{error['loc'][0] if error['loc'] else 'unknown'}: {error['msg']}" for error in e.errors()]
            self.validation_stats['validation_errors']['lap_data'] = errors
            logger.warning(f"Lap data validation failed: {errors}")
            return ValidationResult(False, None, errors)
        except Exception as e:
            self.validation_stats['failed_validations'] += 1
            error_msg = f"Unexpected error during lap data validation: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(False, None, [error_msg])
    
    def validate_coaching_message(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate coaching message with detailed error reporting"""
        try:
            self.validation_stats['total_validations'] += 1
            message = CoachingMessage(**data)
            self.validation_stats['successful_validations'] += 1
            return ValidationResult(True, message)
        except ValidationError as e:
            self.validation_stats['failed_validations'] += 1
            errors = [f"{error['loc'][0] if error['loc'] else 'unknown'}: {error['msg']}" for error in e.errors()]
            self.validation_stats['validation_errors']['coaching_message'] = errors
            logger.warning(f"Coaching message validation failed: {errors}")
            return ValidationResult(False, None, errors)
        except Exception as e:
            self.validation_stats['failed_validations'] += 1
            error_msg = f"Unexpected error during coaching message validation: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(False, None, [error_msg])
    
    def validate_event(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate event data with detailed error reporting"""
        try:
            self.validation_stats['total_validations'] += 1
            event = validate_event_data(data)
            self.validation_stats['successful_validations'] += 1
            return ValidationResult(True, event)
        except ValidationError as e:
            self.validation_stats['failed_validations'] += 1
            errors = [f"{error['loc'][0] if error['loc'] else 'unknown'}: {error['msg']}" for error in e.errors()]
            self.validation_stats['validation_errors']['event'] = errors
            logger.warning(f"Event validation failed: {errors}")
            return ValidationResult(False, None, errors)
        except Exception as e:
            self.validation_stats['failed_validations'] += 1
            error_msg = f"Unexpected error during event validation: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(False, None, [error_msg])
    
    def validate_batch_telemetry(self, telemetry_list: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate a batch of telemetry data"""
        results = []
        for i, telemetry in enumerate(telemetry_list):
            result = self.validate_telemetry(telemetry)
            if not result.is_valid:
                logger.warning(f"Telemetry {i} validation failed: {result.errors}")
            results.append(result)
        return results
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        total = self.validation_stats['total_validations']
        success_rate = (self.validation_stats['successful_validations'] / total * 100) if total > 0 else 0
        
        return {
            'total_validations': total,
            'successful_validations': self.validation_stats['successful_validations'],
            'failed_validations': self.validation_stats['failed_validations'],
            'success_rate': success_rate,
            'validation_errors': self.validation_stats['validation_errors']
        }

class DataTransformer:
    """Data transformation utilities for schema compatibility"""
    
    @staticmethod
    def transform_legacy_telemetry(legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform legacy telemetry format to new schema"""
        transformed = {}
        
        # Map legacy field names to new schema
        field_mapping = {
            'lap_distance_pct': 'lapDistPct',
            'brake_pct': 'brake',
            'throttle_pct': 'throttle',
            'steering_angle': 'steering',
            'current_lap_time': 'lapCurrentLapTime',
            'last_lap_time': 'lapLastLapTime',
            'best_lap_time': 'lapBestLapTime'
        }
        
        for legacy_field, new_field in field_mapping.items():
            if legacy_field in legacy_data:
                transformed[new_field] = legacy_data[legacy_field]
        
        # Copy other fields directly
        for field, value in legacy_data.items():
            if field not in field_mapping:
                transformed[field] = value
        
        # Ensure required fields exist
        if 'timestamp' not in transformed:
            transformed['timestamp'] = time.time()
        
        return transformed
    
    @staticmethod
    def transform_legacy_lap_data(legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform legacy lap data format to new schema"""
        transformed = {}
        
        # Map legacy field names
        field_mapping = {
            'lap_num': 'lap_number',
            'lap_time_seconds': 'lap_time',
            'sector_times_seconds': 'sector_times',
            'telemetry_data': 'telemetry_points'
        }
        
        for legacy_field, new_field in field_mapping.items():
            if legacy_field in legacy_data:
                transformed[new_field] = legacy_data[legacy_field]
        
        # Copy other fields directly
        for field, value in legacy_data.items():
            if field not in field_mapping:
                transformed[field] = value
        
        # Ensure required fields exist
        if 'timestamp' not in transformed:
            transformed['timestamp'] = time.time()
        if 'is_valid' not in transformed:
            transformed['is_valid'] = True
        
        return transformed
    
    @staticmethod
    def transform_legacy_coaching_message(legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform legacy coaching message format to new schema"""
        transformed = {}
        
        # Map legacy field names
        field_mapping = {
            'message': 'content',
            'priority_level': 'priority',
            'message_source': 'source',
            'confidence_level': 'confidence',
            'message_context': 'context'
        }
        
        for legacy_field, new_field in field_mapping.items():
            if legacy_field in legacy_data:
                transformed[new_field] = legacy_data[legacy_field]
        
        # Copy other fields directly
        for field, value in legacy_data.items():
            if field not in field_mapping:
                transformed[field] = value
        
        # Ensure required fields exist
        if 'timestamp' not in transformed:
            transformed['timestamp'] = time.time()
        if 'delivered' not in transformed:
            transformed['delivered'] = False
        if 'attempts' not in transformed:
            transformed['attempts'] = 0
        
        return transformed

class SchemaMigration:
    """Schema migration utilities for version compatibility"""
    
    @staticmethod
    def migrate_telemetry_schema(version: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate telemetry data to current schema version"""
        if version == "1.0":
            # Migration from v1.0 to current
            return DataTransformer.transform_legacy_telemetry(data)
        elif version == "2.0":
            # Migration from v2.0 to current
            return data  # Already compatible
        else:
            raise ValueError(f"Unknown schema version: {version}")
    
    @staticmethod
    def migrate_lap_data_schema(version: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate lap data to current schema version"""
        if version == "1.0":
            # Migration from v1.0 to current
            return DataTransformer.transform_legacy_lap_data(data)
        elif version == "2.0":
            # Migration from v2.0 to current
            return data  # Already compatible
        else:
            raise ValueError(f"Unknown schema version: {version}")
    
    @staticmethod
    def get_schema_version(data: Dict[str, Any]) -> str:
        """Detect schema version from data structure"""
        # Check for version field
        if 'schema_version' in data:
            return data['schema_version']
        
        # Detect version based on field names
        if 'lap_distance_pct' in data or 'brake_pct' in data:
            return "1.0"  # Legacy format
        elif 'lapDistPct' in data or 'brake' in data:
            return "2.0"  # Current format
        else:
            return "unknown"

class PerformanceMonitor:
    """Monitor validation performance and provide insights"""
    
    def __init__(self):
        self.validation_times = []
        self.error_counts = {}
        self.schema_usage = {}
    
    def record_validation_time(self, schema_type: str, duration: float):
        """Record validation time for performance analysis"""
        self.validation_times.append({
            'schema_type': schema_type,
            'duration': duration,
            'timestamp': time.time()
        })
    
    def record_error(self, schema_type: str, error_type: str):
        """Record validation errors for analysis"""
        if schema_type not in self.error_counts:
            self.error_counts[schema_type] = {}
        if error_type not in self.error_counts[schema_type]:
            self.error_counts[schema_type][error_type] = 0
        self.error_counts[schema_type][error_type] += 1
    
    def record_schema_usage(self, schema_type: str):
        """Record schema usage for analytics"""
        if schema_type not in self.schema_usage:
            self.schema_usage[schema_type] = 0
        self.schema_usage[schema_type] += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.validation_times:
            return {}
        
        avg_time = sum(t['duration'] for t in self.validation_times) / len(self.validation_times)
        max_time = max(t['duration'] for t in self.validation_times)
        min_time = min(t['duration'] for t in self.validation_times)
        
        return {
            'total_validations': len(self.validation_times),
            'average_validation_time': avg_time,
            'max_validation_time': max_time,
            'min_validation_time': min_time,
            'error_counts': self.error_counts,
            'schema_usage': self.schema_usage
        }

# Global validator instance
validator = SchemaValidator()
transformer = DataTransformer()
migrator = SchemaMigration()
monitor = PerformanceMonitor()

def validate_and_transform(data: Dict[str, Any], schema_type: str = "telemetry") -> ValidationResult:
    """Convenience function for validation and transformation"""
    start_time = time.time()
    
    # Detect and migrate schema if needed
    version = migrator.get_schema_version(data)
    if version != "2.0" and version != "unknown":
        if schema_type == "telemetry":
            data = migrator.migrate_telemetry_schema(version, data)
        elif schema_type == "lap_data":
            data = migrator.migrate_lap_data_schema(version, data)
        elif schema_type == "coaching_message":
            data = transformer.transform_legacy_coaching_message(data)
    
    # Validate data
    if schema_type == "telemetry":
        result = validator.validate_telemetry(data)
    elif schema_type == "lap_data":
        result = validator.validate_lap_data(data)
    elif schema_type == "coaching_message":
        result = validator.validate_coaching_message(data)
    elif schema_type == "event":
        result = validator.validate_event(data)
    else:
        result = ValidationResult(False, None, [f"Unknown schema type: {schema_type}"])
    
    # Record performance metrics
    duration = time.time() - start_time
    monitor.record_validation_time(schema_type, duration)
    monitor.record_schema_usage(schema_type)
    
    if not result.is_valid:
        monitor.record_error(schema_type, "validation_failed")
    
    return result 