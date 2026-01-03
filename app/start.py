"""
Simple Backend Starter
Just run: python start.py
"""

import os
import sys
import subprocess
import signal

# Change to project directory (parent of app folder)
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_dir)

print("=" * 70)
print("Starting DID++ Backend Server...")
print("=" * 70)
print()

# Start uvicorn with proper Windows signal handling
process = None
try:
    # CREATE_NEW_PROCESS_GROUP flag for Windows to allow Ctrl+C
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    
    process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "app.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8080"
        # Removed --reload for explicit control
    ], creationflags=creationflags)
    
    # Wait for the process
    process.wait()
    
except KeyboardInterrupt:
    print("\n\nStopping server...")
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    print("Server stopped.")

