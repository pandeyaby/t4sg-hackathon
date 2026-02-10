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

API runs at http://localhost:8000 (or 8004 if you pass `--port 8004`)

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

UI runs at http://localhost:3000

### Mobile (Flutter)

```bash
cd mobile
flutter pub get
flutter run -d macos
```

See `mobile/README.md` for iOS, Android, and Web run targets.

## ✨ Features

- 📷 **Quality Assessment** - Blur, glare, brightness, angle detection before processing
- 🔤 **Multilingual OCR** - Hindi, Marathi, English (Google Vision or Tesseract)
- ✅ **Smart Validation** - Fuzzy matching against farmer database
- 📱 **Mobile Ready** - Flutter app for macOS/iOS/Android + Chrome (web)
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
├── mobile/                  # Flutter app (macOS/iOS/Android/web)
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
| `/farmers` | CRUD | Admin-only farmer records |
| `/profiles` | CRUD | Admin-only farmer profiles |
| `/documents` | CRUD | Admin-only document metadata |
| `/admin/google-credentials` | POST | Admin-only Google Vision setup |

## 🧩 Components & How They Connect

### Backend (FastAPI)
- **`/verify`** orchestrates the pipeline: quality → OCR → validation
- **`quality_assessment.py`** runs OpenCV or stub (PIL) quality checks
- **`ocr_pipeline.py`** uses Google Vision or Tesseract CLI fallback
- **`validation_engine.py`** fuzzy‑matches OCR fields to farmer records
- **`db.py`** provides CRUD access to SQLite `farmers.db`

**Data flow**
1. Client uploads image to `/verify`
2. Quality assessment gates bad photos
3. OCR extracts fields
4. Validation matches fields to farmer records
5. Response returns summary + next steps

### Frontend (Next.js)
- Uploads files to `/api/*` which proxy to the backend
- Displays results, quality scores, OCR and validation
- Admin UI for Google Vision credentials
- Sample loader for quick verification demos

### Mobile (Flutter)
- **macOS / iOS / Android / Web**
- Uploads image to `/verify`
- Stores offline documents in local SQLite (Android/iOS/macOS)
- “Sync When Online” re‑submits pending files
- Admin screen to configure Google Vision
- Base URL field for switching environments

## 🔐 Admin Authentication
Admin‑only routes require `X-Admin-Key` header and `ADMIN_API_KEY` set on backend.

## 🧪 Common Dev Ports
- Backend: `8000` (default) or `8004` (used in mobile dev)
- Frontend: `3000`

## 🔄 Extending the Architecture
- **Add new document types**: extend `validation_engine.py` field rules
- **Improve OCR**: enable Google Vision or add language packs to Tesseract CLI
- **Add new data sources**: swap SQLite with Postgres; keep `db.py` interface
- **Mobile offline**: add background sync + conflict resolution in `LocalStore`
- **ML scoring**: plug in model scoring after OCR, before validation
- **Notifications**: add webhook triggers on validation outcomes

## 🎯 Use Case

Farmers for Forests field workers collect documents (land records, bank details) from farmers during site visits. This system:

1. **Checks photo quality** before upload to avoid rejected documents
2. **Extracts key fields** (name, account number, survey number) automatically
3. **Validates against database** using fuzzy matching for typo tolerance
4. **Reduces processing time** from 15 minutes to 30 seconds per document

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, OpenCV (optional), Google Vision / Tesseract CLI
- **Frontend**: Next.js 14, React, Tailwind CSS
- **Mobile**: Flutter, sqflite, file_picker, shared_preferences
- **Matching**: RapidFuzz (fallback to difflib)

## 📄 License

MIT License - Built by Cisco for 'Tech for Social Good Hackathon 2026'

---

*Empowering rural farmers through AI-driven verification* 🌱
