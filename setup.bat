@echo off
echo ========================================
echo PolicyPulse Setup
echo ========================================
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11+
    exit /b 1
)

echo [1/6] Setting up Virtual Environment...
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo [2/6] Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)

echo Checking NumPy version for ChromaDB compatibility...
pip install "numpy<2.0,>=1.26.0" --upgrade --no-deps
if errorlevel 1 (
    echo WARNING: NumPy version check failed
)

echo.
echo [2/6] Creating environment file...
if not exist .env (
    copy .env.example .env
    echo Created .env file. Edit it to add your API keys ^(optional^).
) else (
    echo .env already exists, skipping.
)

echo.
echo [3/6] Creating ChromaDB data directory...
if not exist chromadb_data (
    mkdir chromadb_data
    echo Created chromadb_data directory.
) else (
    echo chromadb_data already exists.
)

echo.
echo [4/6] Initializing ChromaDB...
python -c "from src.chromadb_setup import get_client; get_client(); print('ChromaDB initialized!')"
if errorlevel 1 (
    echo ERROR: ChromaDB initialization failed
    exit /b 1
)

echo.
echo [5/5] Ingesting policy data...
python cli.py ingest-all
if errorlevel 1 (
    echo WARNING: Data ingestion had some issues. Check logs.
)

echo.
echo ========================================
echo Setup Complete! ✅
echo ========================================
echo.
echo Next steps:
echo   1. ^(Optional^) Edit .env to add API keys for enhanced features
echo   2. Start the server: python start.py
echo   3. Open browser: http://localhost:8000
echo.
echo API Keys ^(all optional, system works without them^):
echo   - Google Cloud Translation: https://console.cloud.google.com/
echo   - Gemini API: https://makersuite.google.com/app/apikey
echo   - Twilio: https://www.twilio.com/console
echo.
pause
