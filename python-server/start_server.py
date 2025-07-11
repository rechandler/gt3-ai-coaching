#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GT3 AI Coaching - Server Startup Script
Handles Unicode encoding issues on Windows
"""

import sys
import os
import io

def setup_unicode_support():
    """Configure proper Unicode support for Windows"""
    if sys.platform == 'win32':
        # Set environment variables for Python to use UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # Reconfigure stdout/stderr for UTF-8 if available
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
                print("✓ Unicode support configured")
            except Exception as e:
                print(f"Warning: Could not reconfigure encoding: {e}")
        else:
            # Fallback for older Python versions
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
                print("✓ Unicode support configured (fallback)")
            except Exception as e:
                print(f"Warning: Could not configure UTF-8 encoding: {e}")

def main():
    """Main entry point"""
    print("Starting GT3 AI Coaching Server...")
    
    # Setup Unicode support first
    setup_unicode_support()
    
    # Import and start the telemetry server
    try:
        import importlib.util
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        telemetry_server_path = os.path.join(script_dir, "telemetry-server.py")
        
        spec = importlib.util.spec_from_file_location("telemetry_server", telemetry_server_path)
        telemetry_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(telemetry_module)
        
        server = telemetry_module.GT3TelemetryServer()
        print(f"Server starting on {server.host}:{server.port}")
        
        # Start the async server
        import asyncio
        asyncio.run(server.start_server())
        
    except ImportError as e:
        print(f"Error importing telemetry server: {e}")
        print("Make sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
