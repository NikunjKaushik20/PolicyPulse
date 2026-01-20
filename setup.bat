@echo off
echo Setting up PolicyPulse...


echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Installing Tesseract OCR (required for image-to-text)...
echo Please download and install Tesseract OCR manually from:
echo   https://github.com/tesseract-ocr/tesseract
echo After installation, add the Tesseract install directory (e.g., C:\Program Files\Tesseract-OCR) to your PATH environment variable.
echo If already installed, you can ignore this message.
echo.

echo Starting Qdrant in Docker...
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest

echo Waiting for Qdrant to start...
timeout /t 5 /nobreak

echo Resetting and ingesting database...
python cli.py reset-db
python cli.py ingest-all

echo.
echo Setup complete!
echo.
echo In a new terminal, run:
echo   streamlit run app.py
echo.
echo API server will start now:
echo   uvicorn src.api:app --reload
uvicorn src.api:app --reload
