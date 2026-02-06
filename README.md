# 🌳 Farmers for Forests - Document Verification System

AI-powered document verification for farmer onboarding. Supports Hindi, Marathi, and English documents with quality assessment, OCR extraction, and fuzzy matching validation.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server
cd src && python main.py

# Or with uvicorn
uvicorn src.main:app --reload --port 8000
```

API will be available at http://localhost:8000

## Features

- 📷 **Quality Assessment** - Blur, glare, brightness, angle detection
- 🔤 **Multilingual OCR** - Hindi, Marathi, English (Google Vision or Tesseract)
- ✅ **Smart Validation** - Fuzzy matching against farmer database
- 📱 **REST API** - Easy integration with any frontend

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/verify` | POST | Full verification pipeline |
| `/quality` | POST | Quality assessment only |
| `/ocr` | POST | OCR extraction only |
| `/validate` | POST | Validation only (JSON) |

## Example Usage

```python
import requests

# Full verification
with open("document.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/verify",
        files={"file": f}
    )
    
result = response.json()
print(result["summary"])
print(result["ocr_result"]["fields"])
```

## Configuration

| Env Variable | Default | Description |
|--------------|---------|-------------|
| `USE_GOOGLE_VISION` | `false` | Use Google Cloud Vision API |
| `FARMER_DB_PATH` | `data/farmers.json` | Path to farmer database |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | Path to GCP service account |

## Project Structure

```
t4sg-hackathon/
├── src/
│   ├── main.py              # FastAPI application
│   ├── quality_assessment.py # Image quality checks
│   ├── ocr_pipeline.py      # OCR extraction
│   └── validation_engine.py # Fuzzy matching
├── data/
│   └── farmers.json         # Sample farmer database
├── tests/
├── docs/
├── requirements.txt
├── ARCHITECTURE.md          # Detailed design doc
└── README.md
```

## Team

Built for **Cisco Tech for Social Good Hackathon 2026**

---

*Empowering rural farmers through AI-driven verification*
