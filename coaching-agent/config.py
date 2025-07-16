#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration for the Hybrid Coaching Agent
"""

import os
from typing import Dict, Any

# Default configuration
DEFAULT_CONFIG = {
    'local_config': {
        'model_path': 'models/',
        'confidence_threshold': 0.0,  # Lowered to minimum
        'pattern_detection_sensitivity': 0.0,  # Lowered to minimum
        'message_cooldown': 0.0,  # No cooldown
        'performance_window': 1,  # Smallest window for analysis
    },
    'remote_config': {
        'api_key': os.getenv('OPENAI_API_KEY', ''),
        'model': 'gpt-3.5-turbo',
        'max_requests_per_minute': 5,
        'max_tokens': 150,
        'temperature': 0.7,
        'timeout': 10.0,  # seconds
    },
    'coaching_config': {
        'default_mode': 'beginner',  # Most verbose mode
        'enable_ai_coaching': True,
        'enable_local_coaching': True,
        'message_queue_size': 50,
        'auto_save_interval': 60.0,  # seconds
    },
    'telemetry_config': {
        'buffer_size': 500,  # number of telemetry samples
        'analysis_frequency': 10,  # Hz
        'sector_boundaries': [0.0, 0.33, 0.66, 1.0],
        'corner_detection_threshold': 0.1,  # steering angle
    },
    'message_config': {
        'priority_cooldowns': {
            'critical': 2.0,
            'high': 5.0,
            'medium': 10.0,
            'low': 15.0
        },
        'category_cooldowns': {
            'braking': 8.0,
            'cornering': 12.0,
            'throttle': 6.0,
            'racing_line': 15.0,
            'safety': 2.0,
            'pit_strategy': 30.0,
            'tire_management': 20.0,
            'consistency': 10.0,
            'performance': 8.0
        }
    },
    'session_config': {
        'storage_path': 'coaching_sessions',
        'auto_save_enabled': True,
        'max_session_history': 100,
        'export_format': 'json'
    }
}

# Coaching mode configurations
COACHING_MODES = {
    'beginner': {
        'ai_usage_frequency': 'high',
        'message_tone': 'encouraging',
        'focus_areas': ['basic_technique', 'safety', 'consistency'],
        'complexity_level': 'simple',
        'feedback_frequency': 'frequent'
    },
    'intermediate': {
        'ai_usage_frequency': 'medium',
        'message_tone': 'balanced',
        'focus_areas': ['technique_refinement', 'speed', 'racing_line'],
        'complexity_level': 'moderate',
        'feedback_frequency': 'moderate'
    },
    'advanced': {
        'ai_usage_frequency': 'low',
        'message_tone': 'technical',
        'focus_areas': ['optimization', 'race_craft', 'setup'],
        'complexity_level': 'detailed',
        'feedback_frequency': 'targeted'
    },
    'race': {
        'ai_usage_frequency': 'minimal',
        'message_tone': 'concise',
        'focus_areas': ['strategy', 'positioning', 'immediate_issues'],
        'complexity_level': 'essential',
        'feedback_frequency': 'critical_only'
    }
}

# Track-specific configurations
TRACK_CONFIGS = {
    'silverstone': {
        'sector_boundaries': [0.0, 0.32, 0.65, 1.0],
        'key_corners': {
            'copse': {'position': 0.08, 'type': 'high_speed'},
            'maggotts': {'position': 0.35, 'type': 'medium_speed'},
            'stowe': {'position': 0.62, 'type': 'slow_speed'},
            'club': {'position': 0.88, 'type': 'slow_speed'}
        },
        'optimal_speeds': {
            0.0: 280,   # Start/finish straight
            0.1: 180,   # After Copse
            0.3: 120,   # Maggotts/Becketts
            0.5: 200,   # Hangar straight
            0.7: 100,   # Stowe
            0.9: 160    # After Club
        }
    },
    'spa': {
        'sector_boundaries': [0.0, 0.28, 0.61, 1.0],
        'key_corners': {
            'eau_rouge': {'position': 0.12, 'type': 'high_speed'},
            'les_combes': {'position': 0.31, 'type': 'medium_speed'},
            'pouhon': {'position': 0.45, 'type': 'medium_speed'},
            'chicane': {'position': 0.85, 'type': 'slow_speed'}
        }
    },
    'monza': {
        'sector_boundaries': [0.0, 0.35, 0.70, 1.0],
        'key_corners': {
            'prima_variante': {'position': 0.16, 'type': 'slow_speed'},
            'seconda_variante': {'position': 0.40, 'type': 'slow_speed'},
            'parabolica': {'position': 0.82, 'type': 'medium_speed'}
        }
    }
}

class ConfigManager:
    """Manages configuration for the coaching agent"""
    
    def __init__(self, config_file: str = None):
        self.config = DEFAULT_CONFIG.copy()
        self.config_file = config_file
        
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
    
    def load_config(self, config_file: str):
        """Load configuration from file"""
        try:
            import json
            with open(config_file, 'r') as f:
                user_config = json.load(f)
            
            # Merge with default config
            self._merge_config(self.config, user_config)
            print(f"Loaded configuration from {config_file}")
            
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def save_config(self, config_file: str = None):
        """Save current configuration to file"""
        try:
            import json
            file_path = config_file or self.config_file or 'coaching_config.json'
            
            with open(file_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            print(f"Configuration saved to {file_path}")
            
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config.copy()
    
    def get_mode_config(self, mode: str) -> Dict[str, Any]:
        """Get configuration for specific coaching mode"""
        return COACHING_MODES.get(mode, COACHING_MODES['intermediate'])
    
    def get_track_config(self, track_name: str) -> Dict[str, Any]:
        """Get configuration for specific track"""
        # Normalize track name
        track_key = track_name.lower().replace(' ', '_').replace('-', '_')
        
        # Try exact match first
        if track_key in TRACK_CONFIGS:
            return TRACK_CONFIGS[track_key]
        
        # Try partial matches
        for config_track, config in TRACK_CONFIGS.items():
            if config_track in track_key or track_key in config_track:
                return config
        
        # Return default configuration
        return {
            'sector_boundaries': [0.0, 0.33, 0.66, 1.0],
            'key_corners': {},
            'optimal_speeds': {}
        }
    
    def update_config(self, section: str, updates: Dict[str, Any]):
        """Update a specific configuration section"""
        if section in self.config:
            self.config[section].update(updates)
        else:
            self.config[section] = updates
    
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        try:
            # Validate API key for remote coaching
            if self.config['coaching_config']['enable_ai_coaching']:
                api_key = self.config['remote_config']['api_key']
                if not api_key or api_key == 'your-openai-api-key':
                    print("Warning: No valid OpenAI API key found. AI coaching will be disabled.")
                    self.config['coaching_config']['enable_ai_coaching'] = False
            
            # Validate paths
            model_path = self.config['local_config']['model_path']
            if not os.path.exists(model_path):
                os.makedirs(model_path, exist_ok=True)
                print(f"Created model directory: {model_path}")
            
            storage_path = self.config['session_config']['storage_path']
            if not os.path.exists(storage_path):
                os.makedirs(storage_path, exist_ok=True)
                print(f"Created storage directory: {storage_path}")
            
            return True
            
        except Exception as e:
            print(f"Configuration validation error: {e}")
            return False

# Environment-specific configurations
def get_development_config() -> Dict[str, Any]:
    """Get configuration for development environment"""
    config = DEFAULT_CONFIG.copy()
    config['coaching_config']['auto_save_interval'] = 30.0  # More frequent saves
    config['remote_config']['max_requests_per_minute'] = 10  # Higher limit for testing
    return config

def get_production_config() -> Dict[str, Any]:
    """Get configuration for production environment"""
    config = DEFAULT_CONFIG.copy()
    config['remote_config']['max_requests_per_minute'] = 3  # Conservative limit
    config['coaching_config']['auto_save_interval'] = 120.0  # Less frequent saves
    return config

# Utility functions
def create_default_config_file(filename: str = 'coaching_config.json'):
    """Create a default configuration file"""
    try:
        import json
        with open(filename, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"Created default configuration file: {filename}")
        return True
    except Exception as e:
        print(f"Error creating config file: {e}")
        return False

if __name__ == "__main__":
    # Create default config file
    create_default_config_file()
    
    # Test config manager
    manager = ConfigManager()
    print("Configuration validation:", manager.validate_config())
    
    # Test track config
    silverstone_config = manager.get_track_config("Silverstone Grand Prix")
    print(f"Silverstone config: {silverstone_config}")
    
    # Test mode config
    beginner_config = manager.get_mode_config("beginner")
    print(f"Beginner mode config: {beginner_config}")
