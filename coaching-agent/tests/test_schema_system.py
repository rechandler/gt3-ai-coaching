#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Schema System
==================

Comprehensive test suite for the schema validation system.
Demonstrates type safety, validation, and maintainability as the system scales.

Features tested:
- Pydantic model validation
- Schema evolution and migration
- Error handling and reporting
- Performance monitoring
- Data transformation utilities
"""

import asyncio
import time
import logging
from typing import Dict, List, Any
from schemas import (
    TelemetryData, LapData, SectorData, ReferenceLap, ReferenceType,
    CoachingMessage, CoachingInsight, BaseEvent, EventType,
    MessagePriority, CoachingMode, InsightType
)
from schema_validator import (
    validate_and_transform, SchemaValidator, DataTransformer,
    SchemaMigration, PerformanceMonitor, ValidationResult
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SchemaSystemTester:
    """Comprehensive schema system testing"""
    
    def __init__(self):
        self.validator = SchemaValidator()
        self.transformer = DataTransformer()
        self.migrator = SchemaMigration()
        self.monitor = PerformanceMonitor()
        self.test_results = []
    
    def test_telemetry_validation(self):
        """Test telemetry data validation"""
        logger.info("🧪 Testing telemetry validation...")
        
        # Valid telemetry data
        valid_telemetry = {
            'timestamp': time.time(),
            'lap': 1,
            'lapDistPct': 0.25,
            'speed': 150.0,
            'throttle': 85.0,
            'brake': 0.0,
            'steering': 0.1,
            'gear': 5,
            'rpm': 7000.0,
            'track_name': 'Spa-Francorchamps',
            'car_name': 'BMW M4 GT3',
            'session_type': 'practice',
            'lapCurrentLapTime': 45.123,
            'lapLastLapTime': 90.456,
            'lapBestLapTime': 89.234,
            'fuel_level': 50.0,
            'on_pit_road': False,
            'lapCompleted': False
        }
        
        # Test valid data
        result = validate_and_transform(valid_telemetry, "telemetry")
        self.test_results.append({
            'test': 'valid_telemetry',
            'passed': result.is_valid,
            'errors': result.errors
        })
        
        if result.is_valid:
            logger.info("✅ Valid telemetry validation passed")
        else:
            logger.error(f"❌ Valid telemetry validation failed: {result.errors}")
        
        # Test invalid telemetry data
        invalid_telemetry = {
            'timestamp': -1,  # Invalid timestamp
            'lapDistPct': 1.5,  # Invalid lap distance
            'throttle': 150.0,  # Invalid throttle percentage
            'brake': -10.0,  # Invalid brake percentage
        }
        
        result = validate_and_transform(invalid_telemetry, "telemetry")
        self.test_results.append({
            'test': 'invalid_telemetry',
            'passed': not result.is_valid,  # Should fail validation
            'errors': result.errors
        })
        
        if not result.is_valid:
            logger.info("✅ Invalid telemetry correctly rejected")
        else:
            logger.error("❌ Invalid telemetry should have been rejected")
    
    def test_lap_data_validation(self):
        """Test lap data validation"""
        logger.info("🧪 Testing lap data validation...")
        
        # Create valid telemetry points
        telemetry_points = [
            TelemetryData(
                timestamp=time.time(),
                lap=1,
                lapDistPct=0.1,
                speed=100.0,
                throttle=80.0,
                brake=0.0,
                steering=0.05,
                gear=4,
                rpm=6000.0,
                track_name='Spa-Francorchamps',
                car_name='BMW M4 GT3'
            ),
            TelemetryData(
                timestamp=time.time() + 1,
                lap=1,
                lapDistPct=0.5,
                speed=150.0,
                throttle=90.0,
                brake=0.0,
                steering=0.0,
                gear=5,
                rpm=7000.0,
                track_name='Spa-Francorchamps',
                car_name='BMW M4 GT3'
            )
        ]
        
        # Valid lap data
        valid_lap_data = {
            'lap_number': 1,
            'lap_time': 90.123,
            'sector_times': [30.1, 30.2, 29.823],
            'telemetry_points': telemetry_points,
            'track_name': 'Spa-Francorchamps',
            'car_name': 'BMW M4 GT3',
            'timestamp': time.time(),
            'is_valid': True,
            'metadata': {
                'sector_boundaries': [0.0, 0.33, 0.66, 1.0],
                'telemetry_count': 2
            }
        }
        
        # Test valid lap data
        result = validate_and_transform(valid_lap_data, "lap_data")
        self.test_results.append({
            'test': 'valid_lap_data',
            'passed': result.is_valid,
            'errors': result.errors
        })
        
        if result.is_valid:
            logger.info("✅ Valid lap data validation passed")
        else:
            logger.error(f"❌ Valid lap data validation failed: {result.errors}")
        
        # Test invalid lap data
        invalid_lap_data = {
            'lap_number': 0,  # Invalid lap number
            'lap_time': -10.0,  # Invalid lap time
            'sector_times': [],  # Empty sector times
            'telemetry_points': telemetry_points,
            'track_name': 'Spa-Francorchamps',
            'car_name': 'BMW M4 GT3',
            'timestamp': time.time()
        }
        
        result = validate_and_transform(invalid_lap_data, "lap_data")
        self.test_results.append({
            'test': 'invalid_lap_data',
            'passed': not result.is_valid,  # Should fail validation
            'errors': result.errors
        })
        
        if not result.is_valid:
            logger.info("✅ Invalid lap data correctly rejected")
        else:
            logger.error("❌ Invalid lap data should have been rejected")
    
    def test_coaching_message_validation(self):
        """Test coaching message validation"""
        logger.info("🧪 Testing coaching message validation...")
        
        # Valid coaching message
        valid_message = {
            'content': 'Great lap! You improved by 0.5 seconds.',
            'category': 'lap_timing',
            'priority': MessagePriority.HIGH,
            'source': 'lap_buffer',
            'confidence': 0.9,
            'context': 'lap_completion',
            'timestamp': time.time(),
            'delivered': False,
            'attempts': 0
        }
        
        # Test valid message
        result = validate_and_transform(valid_message, "coaching_message")
        self.test_results.append({
            'test': 'valid_coaching_message',
            'passed': result.is_valid,
            'errors': result.errors
        })
        
        if result.is_valid:
            logger.info("✅ Valid coaching message validation passed")
        else:
            logger.error(f"❌ Valid coaching message validation failed: {result.errors}")
        
        # Test invalid coaching message
        invalid_message = {
            'content': '',  # Empty content
            'category': 'lap_timing',
            'priority': MessagePriority.HIGH,
            'source': 'lap_buffer',
            'confidence': 1.5,  # Invalid confidence
            'context': 'lap_completion',
            'timestamp': time.time()
        }
        
        result = validate_and_transform(invalid_message, "coaching_message")
        self.test_results.append({
            'test': 'invalid_coaching_message',
            'passed': not result.is_valid,  # Should fail validation
            'errors': result.errors
        })
        
        if not result.is_valid:
            logger.info("✅ Invalid coaching message correctly rejected")
        else:
            logger.error("❌ Invalid coaching message should have been rejected")
    
    def test_schema_migration(self):
        """Test schema migration utilities"""
        logger.info("🧪 Testing schema migration...")
        
        # Legacy telemetry format
        legacy_telemetry = {
            'timestamp': time.time(),
            'lap_distance_pct': 0.25,
            'brake_pct': 0.0,
            'throttle_pct': 85.0,
            'steering_angle': 0.1,
            'current_lap_time': 45.123,
            'last_lap_time': 90.456,
            'best_lap_time': 89.234,
            'speed': 150.0,
            'gear': 5,
            'rpm': 7000.0
        }
        
        # Test migration
        migrated = self.migrator.migrate_telemetry_schema("1.0", legacy_telemetry)
        result = validate_and_transform(migrated, "telemetry")
        
        self.test_results.append({
            'test': 'schema_migration',
            'passed': result.is_valid,
            'errors': result.errors
        })
        
        if result.is_valid:
            logger.info("✅ Schema migration successful")
        else:
            logger.error(f"❌ Schema migration failed: {result.errors}")
    
    def test_data_transformation(self):
        """Test data transformation utilities"""
        logger.info("🧪 Testing data transformation...")
        
        # Legacy coaching message format
        legacy_message = {
            'message': 'Great lap!',
            'priority_level': 'high',
            'message_source': 'lap_buffer',
            'confidence_level': 0.9,
            'message_context': 'lap_completion',
            'category': 'lap_timing',  # Add required category field
            'timestamp': time.time()
        }
        
        # Test transformation
        transformed = self.transformer.transform_legacy_coaching_message(legacy_message)
        result = validate_and_transform(transformed, "coaching_message")
        
        self.test_results.append({
            'test': 'data_transformation',
            'passed': result.is_valid,
            'errors': result.errors
        })
        
        if result.is_valid:
            logger.info("✅ Data transformation successful")
        else:
            logger.error(f"❌ Data transformation failed: {result.errors}")
    
    def test_batch_validation(self):
        """Test batch validation performance"""
        logger.info("🧪 Testing batch validation...")
        
        # Generate batch of telemetry data
        telemetry_batch = []
        for i in range(100):
            telemetry = {
                'timestamp': time.time() + i,
                'lap': 1,
                'lapDistPct': (i % 100) / 100.0,
                'speed': 100.0 + (i % 50),
                'throttle': 80.0 + (i % 20),
                'brake': i % 10,
                'steering': (i % 10) / 10.0,
                'gear': 3 + (i % 3),
                'rpm': 5000.0 + (i % 2000),
                'track_name': 'Spa-Francorchamps',
                'car_name': 'BMW M4 GT3'
            }
            telemetry_batch.append(telemetry)
        
        # Test batch validation
        start_time = time.time()
        results = self.validator.validate_batch_telemetry(telemetry_batch)
        duration = time.time() - start_time
        
        valid_count = sum(1 for r in results if r.is_valid)
        error_count = len(results) - valid_count
        
        self.test_results.append({
            'test': 'batch_validation',
            'passed': valid_count == len(results),
            'performance': {
                'total_items': len(results),
                'valid_items': valid_count,
                'error_items': error_count,
                'duration': duration,
                'items_per_second': len(results) / duration
            }
        })
        
        logger.info(f"✅ Batch validation completed: {valid_count}/{len(results)} valid in {duration:.3f}s")
    
    def test_performance_monitoring(self):
        """Test performance monitoring"""
        logger.info("🧪 Testing performance monitoring...")
        
        # Simulate various validation operations
        for i in range(50):
            telemetry = {
                'timestamp': time.time(),
                'lap': 1,
                'lapDistPct': 0.25,
                'speed': 150.0,
                'throttle': 85.0,
                'brake': 0.0,
                'steering': 0.1,
                'gear': 5,
                'rpm': 7000.0,
                'track_name': 'Spa-Francorchamps',
                'car_name': 'BMW M4 GT3'
            }
            
            result = validate_and_transform(telemetry, "telemetry")
            
            # Simulate some errors
            if i % 10 == 0:
                invalid_telemetry = {'timestamp': -1}
                validate_and_transform(invalid_telemetry, "telemetry")
        
        # Get performance stats
        stats = self.monitor.get_performance_stats()
        
        self.test_results.append({
            'test': 'performance_monitoring',
            'passed': stats.get('total_validations', 0) > 0,
            'stats': stats
        })
        
        logger.info(f"✅ Performance monitoring: {stats.get('total_validations', 0)} validations recorded")
    
    def test_error_handling(self):
        """Test comprehensive error handling"""
        logger.info("🧪 Testing error handling...")
        
        # Test various error conditions
        error_tests = [
            {
                'name': 'missing_required_fields',
                'data': {},  # Completely empty data - should fail validation
                'schema_type': 'telemetry'
            },
            {
                'name': 'invalid_field_types',
                'data': {
                    'timestamp': 'invalid_timestamp',
                    'lap': 'not_a_number',
                    'speed': 'not_a_float'
                },
                'schema_type': 'telemetry'
            },
            {
                'name': 'out_of_range_values',
                'data': {
                    'timestamp': time.time(),
                    'lapDistPct': 1.5,  # Out of range
                    'throttle': 150.0,  # Out of range
                    'brake': -10.0  # Out of range
                },
                'schema_type': 'telemetry'
            }
        ]
        
        error_handling_passed = True
        
        for test in error_tests:
            result = validate_and_transform(test['data'], test['schema_type'])
            
            if result.is_valid:
                logger.error(f"❌ {test['name']} should have failed validation")
                error_handling_passed = False
            else:
                logger.info(f"✅ {test['name']} correctly rejected with errors: {result.errors}")
        
        self.test_results.append({
            'test': 'error_handling',
            'passed': error_handling_passed,
            'error_tests': len(error_tests)
        })
    
    def run_all_tests(self):
        """Run all schema system tests"""
        logger.info("🚀 Starting comprehensive schema system tests...")
        
        try:
            self.test_telemetry_validation()
            self.test_lap_data_validation()
            self.test_coaching_message_validation()
            self.test_schema_migration()
            self.test_data_transformation()
            self.test_batch_validation()
            self.test_performance_monitoring()
            self.test_error_handling()
            
            # Generate test report
            self.generate_test_report()
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            raise
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("\n📊 Test Report:")
        logger.info("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['passed'])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        for i, result in enumerate(self.test_results, 1):
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            logger.info(f"{i:2d}. {result['test']:<25} {status}")
            
            if not result['passed'] and 'errors' in result:
                for error in result['errors']:
                    logger.info(f"     Error: {error}")
            
            if 'performance' in result:
                perf = result['performance']
                logger.info(f"     Performance: {perf['items_per_second']:.1f} items/sec")
        
        # Validation statistics
        validator_stats = self.validator.get_validation_stats()
        logger.info(f"\nValidation Statistics:")
        logger.info(f"Total validations: {validator_stats['total_validations']}")
        logger.info(f"Success rate: {validator_stats['success_rate']:.1f}%")
        
        # Performance statistics
        monitor_stats = self.monitor.get_performance_stats()
        if monitor_stats:
            logger.info(f"\nPerformance Statistics:")
            logger.info(f"Average validation time: {monitor_stats['average_validation_time']:.6f}s")
            logger.info(f"Max validation time: {monitor_stats['max_validation_time']:.6f}s")
            logger.info(f"Min validation time: {monitor_stats['min_validation_time']:.6f}s")
        
        logger.info("\n🎉 Schema system test suite completed!")

async def main():
    """Main test runner"""
    logger.info("🧪 Starting Schema System Test Suite...")
    
    tester = SchemaSystemTester()
    tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 