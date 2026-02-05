@echo off
echo ========================================
echo Fixing ChromaDB Database
echo ========================================
echo.
echo This will delete and recreate the ChromaDB database.
echo You will need to re-ingest data after this.
echo.
pause

echo Stopping any running servers...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq PolicyPulse*" 2>nul

echo Deleting old ChromaDB data...
if exist chromadb_data (
    rmdir /S /Q chromadb_data
    echo Old database deleted.
) else (
    echo No old database found.
)

echo Creating fresh ChromaDB directory...
mkdir chromadb_data

echo Initializing ChromaDB...
python -c "from src.chromadb_setup import get_client; get_client(); print('ChromaDB initialized!')"
if errorlevel 1 (
    echo ERROR: ChromaDB initialization failed
    pause
    exit /b 1
)

echo.
echo Ingesting policy data...
python cli.py ingest-all
if errorlevel 1 (
    echo WARNING: Data ingestion had some issues. Check logs.
)

echo.
echo ========================================
echo Database Fixed! ✅
echo ========================================
echo.
echo You can now start the server: python start.py
echo.
pause
