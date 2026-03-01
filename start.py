"""
PolicyPulse - Start Server
Delegates to start_amd.py for AMD-optimized startup.
For simple dev use: python start.py --dev
For production: python start_amd.py
"""
import os
import sys
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    # Redirect to AMD-optimized startup
    print("Tip: For AMD EPYC/Instinct optimized startup use: python start_amd.py")
    print("Starting basic server...")

    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
