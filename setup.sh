#!/bin/bash

echo "Setting up PolicyPulse..."

pip install -r requirements.txt

docker run -d -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant:latest

echo "Installing Tesseract OCR (required for image-to-text)..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update && sudo apt-get install -y tesseract-ocr libtesseract-dev libleptonica-dev
elif command -v yum &> /dev/null; then
    sudo yum install -y tesseract
else
    echo "Please install Tesseract OCR manually for your OS. See https://github.com/tesseract-ocr/tesseract"
fi

echo "Waiting for Qdrant to start..."
sleep 5

echo "Resetting and ingesting database..."
python cli.py reset-db
python cli.py ingest-all

echo
echo "Setup complete!"
echo
echo "In a new terminal, run:"
echo "  streamlit run app.py"
echo
echo "API server will start now:"
echo "  uvicorn src.api:app --reload"
uvicorn src.api:app --reload

echo "Setup complete! Run: streamlit run app.py"
