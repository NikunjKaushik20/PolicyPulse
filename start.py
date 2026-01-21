import subprocess
import sys
import time

# Start FastAPI (internal)
subprocess.Popen(
    [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
)

# Give FastAPI time to start
time.sleep(3)

# Start Streamlit (public)
subprocess.run(
    [
        "streamlit",
        "run",
        "app.py",
        "--server.address=0.0.0.0",
        "--server.port=8501",
    ]
)
