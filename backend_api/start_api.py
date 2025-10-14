#!/usr/bin/env python3
"""
Startup script for the UAV Log Viewer Backend API
"""

import sys
import os
import subprocess

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import flask
        import flask_cors
        print("✓ Flask and Flask-CORS are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please install dependencies with: pip install -r requirements.txt")
        return False

def start_api():
    """Start the Flask API server"""
    if not check_dependencies():
        sys.exit(1)
    
    print("Starting UAV Log Viewer Backend API...")
    print("API will be available at: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        from app import app
        app.run(host='0.0.0.0', port=8000, debug=True)
    except KeyboardInterrupt:
        print("\nShutting down API server...")
    except Exception as e:
        print(f"Error starting API: {e}")
        sys.exit(1)

if __name__ == '__main__':
    start_api()
