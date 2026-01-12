#!/usr/bin/env python3
"""
Convenience script to run the Aionix Agent backend.

This script provides an easy way to start the backend application
with proper working directory setup.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the backend application."""
    # Change to backend directory
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)

    # Set Python path to include backend directory
    sys.path.insert(0, str(backend_dir))

    # Run uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]

    print("Starting Aionix Agent Backend...")
    print(f"Working directory: {backend_dir}")
    print(f"Command: {' '.join(cmd)}")
    print("\nAPI Documentation will be available at:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print("  - Health Check: http://localhost:8000/health/ready")
    print("\nPress Ctrl+C to stop the server\n")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nShutting down backend...")
    except Exception as e:
        print(f"Error starting backend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
