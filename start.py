"""
PolicyPulse - Start Server

Simple startup script that launches the FastAPI server.
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("=" * 50)
    print("PolicyPulse - Community Impact Platform")
    print("=" * 50)
    print()
    print("Starting FastAPI server...")
    print("API documentation: http://localhost:8000/docs")
    print("Main UI: http://localhost:8000")
    print()
    print("Press CTRL+C to stop the server")
    print()
    
    # Check if API keys are configured
    api_keys_configured = []
    if os.getenv("GOOGLE_CLOUD_TRANSLATE_KEY"):
        api_keys_configured.append("Google Translate")
    if os.getenv("GEMINI_API_KEY"):
        api_keys_configured.append("Gemini LLM")
    if os.getenv("TWILIO_ACCOUNT_SID"):
        api_keys_configured.append("Twilio")
    
    if api_keys_configured:
        print(f"✅ Enhanced features enabled: {', '.join(api_keys_configured)}")
    else:
        print("ℹ️  Running in basic mode (no API keys configured)")
        print("   To enable enhanced features, edit .env file")
    print()
    
    # Start server
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
