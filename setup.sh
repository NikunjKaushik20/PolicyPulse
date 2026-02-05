#!/bin/bash

echo "========================================"
echo "PolicyPulse Setup"
echo "========================================"
echo

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found. Please install Python 3.11+"
    exit 1
fi

echo "[1/6] Installing Python dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo "Checking NumPy version for ChromaDB compatibility..."
pip3 install "numpy<2.0,>=1.26.0" --upgrade --no-deps
if [ $? -ne 0 ]; then
    echo "WARNING: NumPy version check failed"
fi

echo
echo "[2/6] Creating environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Edit it to add your API keys (optional)."
else
    echo ".env already exists, skipping."
fi

echo
echo "[3/6] Creating ChromaDB data directory..."
if [ ! -d chromadb_data ]; then
    mkdir chromadb_data
    echo "Created chromadb_data directory."
else
    echo "chromadb_data already exists."
fi

echo
echo "[4/6] Initializing ChromaDB..."
python3 -c "from src.chromadb_setup import get_client; get_client(); print('ChromaDB initialized!')"
if [ $? -ne 0 ]; then
    echo "ERROR: ChromaDB initialization failed"
    exit 1
fi

echo
echo "[5/6] Running data migration (if Qdrant data exists)..."
python3 migrate_to_chromadb.py

echo
echo "[6/6] Ingesting policy data..."
python3 cli.py ingest-all
if [ $? -ne 0 ]; then
    echo "WARNING: Data ingestion had some issues. Check logs."
fi

echo
echo "========================================"
echo "Setup Complete! (No Docker needed) ✅"
echo "========================================"
echo
echo "Next steps:"
echo "  1. (Optional) Edit .env to add API keys for enhanced features"
echo "  2. Start the server: python3 start.py"
echo "  3. Open browser: http://localhost:8000"
echo
echo "API Keys (all optional, system works without them):"
echo "  - Google Cloud Translation: https://console.cloud.google.com/"
echo "  - Gemini API: https://makersuite.google.com/app/apikey"
echo "  - Twilio: https://www.twilio.com/console"
echo
