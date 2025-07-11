#!/usr/bin/env python3
"""
Pre-build script to prepare the application for packaging
Optimizes Python dependencies and creates distribution-ready build
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    print("🔧 Preparing GT3 AI Coaching for distribution...")
    
    # Get project root
    project_root = Path(__file__).parent.parent
    python_server_path = project_root / "python-server"
    build_path = project_root / "build"
    
    # Check if build exists
    if not build_path.exists():
        print("❌ Build directory not found. Please run 'npm run build' first.")
        return False
    
    print("✅ Build directory found")
    
    # Create requirements.txt if it doesn't exist
    requirements_file = python_server_path / "requirements.txt"
    if not requirements_file.exists():
        print("📝 Creating requirements.txt...")
        requirements = [
            "numpy>=1.21.0",
            "websockets>=10.0",
            "pyirsdk>=1.0.0"
        ]
        with open(requirements_file, 'w') as f:
            f.write('\n'.join(requirements))
        print("✅ Requirements.txt created")
    
    # Optimize Python files (remove __pycache__, .pyc files)
    print("🧹 Cleaning Python cache files...")
    for root, dirs, files in os.walk(python_server_path):
        # Remove __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))
    
    print("✅ Python files optimized")
    
    # Check Python dependencies
    print("🔍 Checking Python dependencies...")
    try:
        import numpy
        import websockets
        print("✅ Core dependencies available")
    except ImportError as e:
        print(f"⚠️  Missing dependency: {e}")
        print("💡 Users will need to install Python dependencies")
    
    # Create version info
    version_file = project_root / "version.json"
    version_info = {
        "version": "1.0.0",
        "build_date": subprocess.check_output(["date", "/t"], shell=True).decode().strip(),
        "build_time": subprocess.check_output(["time", "/t"], shell=True).decode().strip(),
        "components": {
            "electron_app": True,
            "python_server": True,
            "ai_coach": True
        }
    }
    
    import json
    with open(version_file, 'w') as f:
        json.dump(version_info, f, indent=2)
    
    print("✅ Version info created")
    print("🚀 Application ready for installer packaging!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
