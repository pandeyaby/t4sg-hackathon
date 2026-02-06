# 🌳 Farmers for Forests - Document Verification System

AI-powered document verification for farmer onboarding. Supports Hindi, Marathi, and English documents with quality assessment, OCR extraction, and fuzzy matching validation.

![License](https://img.shields.io/badge/license-MIT-green)
![Hackathon](https://img.shields.io/badge/Cisco-Tech%20for%20Social%20Good%202026-blue)

## 🚀 Quick Start

### Backend (Python FastAPI)

```bash
cd backend
pip install -r requirements.txt
cd src && python main.py
```

API runs at http://localhost:8000

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

UI runs at http://localhost:3000

## ✨ Features

- 📷 **Quality Assessment** - Blur, glare, brightness, angle detection before processing
- 🔤 **Multilingual OCR** - Hindi, Marathi, English (Google Vision or Tesseract)
- ✅ **Smart Validation** - Fuzzy matching against farmer database
- 📱 **Mobile Ready** - Responsive design for field workers
- 🌐 **REST API** - Easy integration with any system

## 📁 Project Structure

```
├── backend/                 # Python FastAPI
│   ├── src/
│   │   ├── main.py                 # API endpoints
│   │   ├── quality_assessment.py   # Image quality checks
│   │   ├── ocr_pipeline.py         # Multilingual OCR
│   │   └── validation_engine.py    # Fuzzy matching
│   ├── data/
│   │   └── farmers.json            # Sample database
│   └── requirements.txt
│
├── frontend/                # Next.js + Tailwind
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── package.json
│   └── tailwind.config.ts
│
├── ARCHITECTURE.md          # Technical design
└── README.md
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/verify` | POST | Full verification pipeline |
| `/quality` | POST | Quality assessment only |
| `/ocr` | POST | OCR extraction only |
| `/validate` | POST | Validation only (JSON) |

## 🎯 Use Case

Farmers for Forests field workers collect documents (land records, bank details) from farmers during site visits. This system:

1. **Checks photo quality** before upload to avoid rejected documents
2. **Extracts key fields** (name, account number, survey number) automatically
3. **Validates against database** using fuzzy matching for typo tolerance
4. **Reduces processing time** from 15 minutes to 30 seconds per document

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, OpenCV, Google Cloud Vision / Tesseract
- **Frontend**: Next.js 14, React, Tailwind CSS
- **Matching**: RapidFuzz for fuzzy string matching

## 📄 License

MIT License - Built for Cisco Tech for Social Good Hackathon 2026

---

*Empowering rural farmers through AI-driven verification* 🌱
