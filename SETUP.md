## Prerequisites

- **Tesseract OCR is required for image-to-text features. Please install it manually before running the setup script.**

### Manual Tesseract Installation

#### Windows
1. Download the Tesseract installer from the official repo: [https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract)
	- Or use the direct installer: [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Run the installer and follow the prompts.
3. After installation, add the Tesseract install directory (e.g., `C:\Program Files\Tesseract-OCR`) to your **PATH** environment variable:
	- Open System Properties → Environment Variables
	- Under 'System variables', find and edit `Path`
	- Add: `C:\Program Files\Tesseract-OCR`
4. Open a new terminal and run `tesseract --version` to verify installation.

#### Linux (Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
tesseract --version
```

---

- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and ensure it is running before running the setup script. Qdrant will be started in Docker.

## Setup Steps

```bash
git clone https://github.com/nikunjkaushik20/policypulse.git
cd policypulse
setup.bat   # On Windows
# or
./setup.sh  # On Linux/macOS
```

Then, in a new terminal:
```bash
streamlit run app.py
```

The API server will start automatically at the end of setup.

## Image Multimodality

You can upload images for embedding and analysis using the `/upload-image` endpoint. Images are embedded using CLIP and stored in Qdrant for multimodal search.

### Example usage:

```bash
curl -X POST "http://localhost:8000/upload-image?policy_id=NREGA&year=2020" \
	-H "accept: application/json" \
	-H "Content-Type: multipart/form-data" \
	-F "file=@/path/to/your/image.jpg"
```
