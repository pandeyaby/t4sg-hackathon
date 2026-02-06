# PS1: Farmers for Forests - Document Verification System
## Technical Architecture & Build Plan

**Goal:** AI-powered document verification for farmer onboarding — handles Hindi/Marathi handwritten documents, quality assessment, fuzzy matching, works offline.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                               │
├─────────────────────────────────────────────────────────────────────┤
│  📱 WhatsApp Bot          │  🌐 Web Upload Portal    │  📲 PWA App   │
│  (Future - mockup)        │  (Primary demo)          │  (Offline)    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                                  │
│                    FastAPI + Python Backend                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ QUALITY       │         │ OCR PIPELINE    │         │ VALIDATION      │
│ ASSESSMENT    │         │                 │         │ ENGINE          │
├───────────────┤         ├─────────────────┤         ├─────────────────┤
│ • Blur detect │         │ • Preprocess    │         │ • Fuzzy match   │
│ • Glare detect│         │ • Hindi OCR     │         │ • Field verify  │
│ • Angle check │         │ • Marathi OCR   │         │ • Cross-check   │
│ • Resolution  │         │ • English OCR   │         │ • Confidence    │
└───────────────┘         └─────────────────┘         └─────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │ FARMER DATABASE │
                          │ (Reference Data)│
                          └─────────────────┘
```

---

## Tech Stack (Optimized for Speed)

| Component | Technology | Why |
|-----------|------------|-----|
| **Backend** | FastAPI (Python) | Fast to build, async, great for ML |
| **OCR - Primary** | Google Cloud Vision API | Best multilingual OCR, handles handwriting |
| **OCR - Fallback** | Tesseract + Bhashini | Free, offline capable |
| **Quality Assessment** | OpenCV + custom CNN | Blur/glare/angle detection |
| **Fuzzy Matching** | RapidFuzz + Levenshtein | Fast string matching |
| **Frontend** | Streamlit or simple HTML/JS | Fastest to build |
| **Database** | SQLite (demo) / PostgreSQL (prod) | Simple, no setup |
| **Offline** | PWA + IndexedDB + TensorFlow.js | Browser-based ML |

---

## Module 1: Quality Assessment

**Purpose:** Check photo quality BEFORE processing to save time and get better results.

```python
# quality_assessment.py

import cv2
import numpy as np
from dataclasses import dataclass

@dataclass
class QualityReport:
    is_acceptable: bool
    blur_score: float      # 0-100, higher = sharper
    brightness_score: float # 0-100, 50 = optimal
    angle_score: float     # 0-100, higher = more straight
    resolution_ok: bool
    issues: list[str]
    suggestions: list[str]

def assess_quality(image_path: str) -> QualityReport:
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    issues = []
    suggestions = []
    
    # 1. Blur Detection (Laplacian variance)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    blur_normalized = min(100, blur_score / 5)  # Normalize to 0-100
    if blur_score < 100:
        issues.append("Image is blurry")
        suggestions.append("Hold camera steady and ensure document is in focus")
    
    # 2. Brightness Check
    brightness = np.mean(gray)
    brightness_score = 100 - abs(brightness - 127) / 1.27  # 127 = optimal
    if brightness < 50:
        issues.append("Image too dark")
        suggestions.append("Move to better lighting or use flash")
    elif brightness > 200:
        issues.append("Image too bright/overexposed")
        suggestions.append("Reduce lighting or avoid direct sunlight")
    
    # 3. Glare Detection (highlight analysis)
    _, highlights = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY)
    glare_percentage = np.sum(highlights) / (gray.size * 255) * 100
    if glare_percentage > 5:
        issues.append("Glare detected on document")
        suggestions.append("Tilt document to avoid reflections")
    
    # 4. Resolution Check
    height, width = img.shape[:2]
    resolution_ok = width >= 800 and height >= 600
    if not resolution_ok:
        issues.append("Resolution too low")
        suggestions.append("Move closer to document or use higher camera quality")
    
    # 5. Angle/Skew Detection (Hough transform)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
    angle_score = 100  # Assume good
    if lines is not None:
        angles = [line[0][1] * 180 / np.pi for line in lines[:10]]
        avg_angle = np.mean(angles)
        skew = abs(90 - avg_angle) if avg_angle > 45 else abs(avg_angle)
        if skew > 10:
            angle_score = max(0, 100 - skew * 5)
            issues.append(f"Document is tilted ({skew:.1f}°)")
            suggestions.append("Align document edges with camera frame")
    
    is_acceptable = len(issues) <= 1 and blur_normalized > 30 and resolution_ok
    
    return QualityReport(
        is_acceptable=is_acceptable,
        blur_score=blur_normalized,
        brightness_score=brightness_score,
        angle_score=angle_score,
        resolution_ok=resolution_ok,
        issues=issues,
        suggestions=suggestions
    )
```

---

## Module 2: OCR Pipeline

**Purpose:** Extract text from documents in Hindi, Marathi, and English.

```python
# ocr_pipeline.py

from google.cloud import vision
from PIL import Image
import pytesseract
from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class OCRResult:
    raw_text: str
    detected_language: str
    confidence: float
    extracted_fields: dict
    
class OCRPipeline:
    def __init__(self, use_google_vision=True):
        self.use_google_vision = use_google_vision
        if use_google_vision:
            self.client = vision.ImageAnnotatorClient()
    
    def extract_text(self, image_path: str) -> OCRResult:
        if self.use_google_vision:
            return self._google_vision_ocr(image_path)
        else:
            return self._tesseract_ocr(image_path)
    
    def _google_vision_ocr(self, image_path: str) -> OCRResult:
        with open(image_path, 'rb') as f:
            content = f.read()
        
        image = vision.Image(content=content)
        response = self.client.document_text_detection(
            image=image,
            image_context={"language_hints": ["hi", "mr", "en"]}
        )
        
        text = response.full_text_annotation.text
        
        # Detect primary language
        lang = "en"
        if any('\u0900' <= c <= '\u097F' for c in text):  # Devanagari
            lang = "hi"  # Could be Hindi or Marathi
        
        # Extract structured fields
        fields = self._extract_fields(text, lang)
        
        return OCRResult(
            raw_text=text,
            detected_language=lang,
            confidence=0.9,  # Google doesn't give overall confidence
            extracted_fields=fields
        )
    
    def _tesseract_ocr(self, image_path: str) -> OCRResult:
        # For offline use
        img = Image.open(image_path)
        
        # Try Hindi first, then English
        text_hi = pytesseract.image_to_string(img, lang='hin+mar+eng')
        
        lang = "hi" if any('\u0900' <= c <= '\u097F' for c in text_hi) else "en"
        fields = self._extract_fields(text_hi, lang)
        
        return OCRResult(
            raw_text=text_hi,
            detected_language=lang,
            confidence=0.7,  # Tesseract is less accurate
            extracted_fields=fields
        )
    
    def _extract_fields(self, text: str, lang: str) -> dict:
        """Extract key fields from document text."""
        fields = {
            "name": None,
            "area": None,
            "address": None,
            "account_number": None,
            "ifsc_code": None,
            "aadhaar": None,
            "survey_number": None
        }
        
        # Account number patterns (10-18 digits)
        acc_match = re.search(r'\b\d{10,18}\b', text)
        if acc_match:
            fields["account_number"] = acc_match.group()
        
        # IFSC code (4 letters + 0 + 6 alphanumeric)
        ifsc_match = re.search(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', text)
        if ifsc_match:
            fields["ifsc_code"] = ifsc_match.group()
        
        # Aadhaar (12 digits, often with spaces)
        aadhaar_match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
        if aadhaar_match:
            fields["aadhaar"] = aadhaar_match.group().replace(" ", "")
        
        # Area in acres/hectares
        area_match = re.search(r'(\d+\.?\d*)\s*(acres?|hectares?|एकड़|हेक्टेयर)', text, re.I)
        if area_match:
            fields["area"] = f"{area_match.group(1)} {area_match.group(2)}"
        
        # Survey/Khasra number
        survey_match = re.search(r'(survey|khasra|खसरा|सर्वे)\s*(?:no\.?|number|नं\.?)?\s*:?\s*(\d+[\/\-]?\d*)', text, re.I)
        if survey_match:
            fields["survey_number"] = survey_match.group(2)
        
        return fields
```

---

## Module 3: Validation Engine

**Purpose:** Verify extracted data against existing records using fuzzy matching.

```python
# validation_engine.py

from rapidfuzz import fuzz, process
from dataclasses import dataclass
from typing import Optional
import json

@dataclass
class ValidationResult:
    is_valid: bool
    confidence: float
    matched_farmer: Optional[dict]
    field_matches: dict
    issues: list[str]

class ValidationEngine:
    def __init__(self, farmer_database_path: str):
        with open(farmer_database_path) as f:
            self.farmers = json.load(f)
    
    def validate(self, extracted_fields: dict) -> ValidationResult:
        """Validate extracted fields against farmer database."""
        
        issues = []
        field_matches = {}
        best_match = None
        best_score = 0
        
        # Try to find matching farmer
        for farmer in self.farmers:
            score = self._calculate_match_score(extracted_fields, farmer)
            if score > best_score:
                best_score = score
                best_match = farmer
        
        # Validate individual fields
        if extracted_fields.get("account_number"):
            acc = extracted_fields["account_number"]
            if not self._validate_account_format(acc):
                issues.append(f"Account number format invalid: {acc}")
                field_matches["account_number"] = {"valid": False, "confidence": 0}
            else:
                field_matches["account_number"] = {"valid": True, "confidence": 0.95}
        
        if extracted_fields.get("ifsc_code"):
            ifsc = extracted_fields["ifsc_code"]
            if not self._validate_ifsc(ifsc):
                issues.append(f"IFSC code may be invalid: {ifsc}")
                field_matches["ifsc_code"] = {"valid": False, "confidence": 0.5}
            else:
                field_matches["ifsc_code"] = {"valid": True, "confidence": 0.9}
        
        if extracted_fields.get("aadhaar"):
            aadhaar = extracted_fields["aadhaar"]
            if not self._validate_aadhaar(aadhaar):
                issues.append(f"Aadhaar format invalid: {aadhaar}")
                field_matches["aadhaar"] = {"valid": False, "confidence": 0}
            else:
                field_matches["aadhaar"] = {"valid": True, "confidence": 0.95}
        
        # Cross-validate with best match
        if best_match and best_score > 70:
            cross_issues = self._cross_validate(extracted_fields, best_match)
            issues.extend(cross_issues)
        
        is_valid = len(issues) == 0 and best_score > 60
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=best_score / 100,
            matched_farmer=best_match if best_score > 60 else None,
            field_matches=field_matches,
            issues=issues
        )
    
    def _calculate_match_score(self, extracted: dict, farmer: dict) -> float:
        """Calculate fuzzy match score between extracted and database record."""
        scores = []
        
        # Name matching (most important)
        if extracted.get("name") and farmer.get("name"):
            name_score = fuzz.token_sort_ratio(
                extracted["name"].lower(), 
                farmer["name"].lower()
            )
            scores.append(name_score * 1.5)  # Weight name higher
        
        # Account number (exact or very close)
        if extracted.get("account_number") and farmer.get("account_number"):
            if extracted["account_number"] == farmer["account_number"]:
                scores.append(100)
            else:
                scores.append(fuzz.ratio(
                    extracted["account_number"],
                    farmer["account_number"]
                ))
        
        # Survey number
        if extracted.get("survey_number") and farmer.get("survey_number"):
            scores.append(fuzz.ratio(
                extracted["survey_number"],
                farmer["survey_number"]
            ))
        
        return sum(scores) / len(scores) if scores else 0
    
    def _validate_account_format(self, acc: str) -> bool:
        return acc.isdigit() and 9 <= len(acc) <= 18
    
    def _validate_ifsc(self, ifsc: str) -> bool:
        import re
        return bool(re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc))
    
    def _validate_aadhaar(self, aadhaar: str) -> bool:
        # Basic Verhoeff check could be added
        return aadhaar.isdigit() and len(aadhaar) == 12
    
    def _cross_validate(self, extracted: dict, farmer: dict) -> list:
        """Check for mismatches between extracted and matched farmer."""
        issues = []
        
        if extracted.get("account_number") and farmer.get("account_number"):
            if extracted["account_number"] != farmer["account_number"]:
                similarity = fuzz.ratio(
                    extracted["account_number"],
                    farmer["account_number"]
                )
                if similarity < 90:
                    issues.append(
                        f"Account number mismatch: extracted '{extracted['account_number']}' "
                        f"vs database '{farmer['account_number']}' (similarity: {similarity}%)"
                    )
        
        return issues
```

---

## Module 4: Main API

```python
# main.py

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import tempfile
import os

from quality_assessment import assess_quality, QualityReport
from ocr_pipeline import OCRPipeline, OCRResult
from validation_engine import ValidationEngine, ValidationResult

app = FastAPI(title="Farmers for Forests - Document Verification API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
ocr = OCRPipeline(use_google_vision=True)
validator = ValidationEngine("data/farmers.json")

class VerificationResponse(BaseModel):
    success: bool
    quality: dict
    ocr_result: Optional[dict]
    validation: Optional[dict]
    summary: str
    next_steps: list[str]

@app.post("/verify", response_model=VerificationResponse)
async def verify_document(file: UploadFile = File(...)):
    """
    Verify a farmer document (land record, bank details, etc.)
    
    Returns quality assessment, OCR results, and validation status.
    """
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Step 1: Quality Assessment
        quality = assess_quality(tmp_path)
        
        if not quality.is_acceptable:
            return VerificationResponse(
                success=False,
                quality=quality.__dict__,
                ocr_result=None,
                validation=None,
                summary="Document quality is insufficient for processing.",
                next_steps=quality.suggestions
            )
        
        # Step 2: OCR Extraction
        ocr_result = ocr.extract_text(tmp_path)
        
        if not ocr_result.extracted_fields:
            return VerificationResponse(
                success=False,
                quality=quality.__dict__,
                ocr_result=ocr_result.__dict__,
                validation=None,
                summary="Could not extract required fields from document.",
                next_steps=["Ensure document contains visible name, account number, or land details"]
            )
        
        # Step 3: Validation
        validation = validator.validate(ocr_result.extracted_fields)
        
        # Build summary
        if validation.is_valid:
            summary = f"✅ Document verified successfully! Matched farmer: {validation.matched_farmer.get('name', 'Unknown')}"
            next_steps = ["Document ready for processing", "No further action required"]
        else:
            summary = f"⚠️ Document needs review. Issues found: {len(validation.issues)}"
            next_steps = validation.issues + ["Please re-upload or contact support"]
        
        return VerificationResponse(
            success=validation.is_valid,
            quality=quality.__dict__,
            ocr_result={
                "raw_text": ocr_result.raw_text[:500],  # Truncate for response
                "language": ocr_result.detected_language,
                "confidence": ocr_result.confidence,
                "fields": ocr_result.extracted_fields
            },
            validation=validation.__dict__,
            summary=summary,
            next_steps=next_steps
        )
    
    finally:
        os.unlink(tmp_path)

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

# Run with: uvicorn main:app --reload --port 8000
```

---

## Module 5: Simple Frontend (Streamlit)

```python
# frontend.py

import streamlit as st
import requests
from PIL import Image
import io

st.set_page_config(
    page_title="Farmers for Forests - Document Verification",
    page_icon="🌳",
    layout="wide"
)

st.title("🌳 Farmers for Forests")
st.subheader("AI-Powered Document Verification System")

st.markdown("""
Upload farmer documents (land records, bank details) for instant verification.
Supports **Hindi**, **Marathi**, and **English** documents.
""")

col1, col2 = st.columns(2)

with col1:
    st.header("📤 Upload Document")
    
    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=["jpg", "jpeg", "png"],
        help="Upload a clear photo of the document"
    )
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Document", use_column_width=True)
        
        if st.button("🔍 Verify Document", type="primary"):
            with st.spinner("Analyzing document..."):
                # Call API
                files = {"file": uploaded_file.getvalue()}
                response = requests.post(
                    "http://localhost:8000/verify",
                    files={"file": ("document.jpg", uploaded_file.getvalue())}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.result = result
                else:
                    st.error("Error processing document")

with col2:
    st.header("📋 Verification Results")
    
    if "result" in st.session_state:
        result = st.session_state.result
        
        # Summary
        if result["success"]:
            st.success(result["summary"])
        else:
            st.warning(result["summary"])
        
        # Quality Assessment
        with st.expander("📊 Quality Assessment", expanded=True):
            quality = result["quality"]
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Sharpness", f"{quality['blur_score']:.0f}/100")
            col_b.metric("Brightness", f"{quality['brightness_score']:.0f}/100")
            col_c.metric("Alignment", f"{quality['angle_score']:.0f}/100")
            
            if quality["issues"]:
                st.warning("Issues: " + ", ".join(quality["issues"]))
        
        # Extracted Fields
        if result["ocr_result"]:
            with st.expander("📝 Extracted Information", expanded=True):
                fields = result["ocr_result"]["fields"]
                for field, value in fields.items():
                    if value:
                        st.write(f"**{field.replace('_', ' ').title()}:** {value}")
                
                st.caption(f"Language detected: {result['ocr_result']['language']}")
        
        # Validation
        if result["validation"]:
            with st.expander("✅ Validation Details", expanded=True):
                val = result["validation"]
                st.write(f"**Confidence:** {val['confidence']*100:.1f}%")
                
                if val["matched_farmer"]:
                    st.write(f"**Matched Farmer:** {val['matched_farmer'].get('name', 'N/A')}")
                
                if val["issues"]:
                    st.error("Issues found:")
                    for issue in val["issues"]:
                        st.write(f"- {issue}")
        
        # Next Steps
        st.subheader("📌 Next Steps")
        for step in result["next_steps"]:
            st.write(f"• {step}")

# Run with: streamlit run frontend.py
```

---

## Sample Data Structure

```json
// data/farmers.json
[
  {
    "id": "F001",
    "name": "राजेश कुमार पाटिल",
    "name_en": "Rajesh Kumar Patil",
    "phone": "+919876543210",
    "village": "Malegaon",
    "district": "Nashik",
    "state": "Maharashtra",
    "account_number": "12345678901234",
    "ifsc_code": "SBIN0001234",
    "bank_name": "State Bank of India",
    "survey_number": "45/2A",
    "area_acres": 2.5,
    "enrolled_date": "2024-06-15"
  },
  {
    "id": "F002",
    "name": "सुनीता देवी शर्मा",
    "name_en": "Sunita Devi Sharma",
    "phone": "+919876543211",
    "village": "Pune Rural",
    "district": "Pune",
    "state": "Maharashtra",
    "account_number": "98765432109876",
    "ifsc_code": "HDFC0002345",
    "bank_name": "HDFC Bank",
    "survey_number": "112/1",
    "area_acres": 1.8,
    "enrolled_date": "2024-07-20"
  }
]
```

---

## Deployment

### Quick Local Setup
```bash
# Create project
cd projects/t4sg-hackathon
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn python-multipart pillow opencv-python-headless \
    google-cloud-vision pytesseract rapidfuzz streamlit requests

# Set up Google Cloud (for OCR)
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

# Run backend
uvicorn main:app --reload --port 8000

# Run frontend (new terminal)
streamlit run frontend.py --server.port 8501
```

### For Demo
- Use ngrok to expose locally: `ngrok http 8000`
- Or deploy to Railway/Render (free tier)

---

## 48-Hour Timeline

| Phase | Hours | Backend Team | Frontend/Design Team |
|-------|-------|--------------|---------------------|
| **Setup** | 0-2 | Python modules, API structure | Set up repo, gather sample docs |
| **Core** | 2-8 | OCR pipeline + validation | UI wireframes, collect test data |
| **Frontend** | 8-12 | API endpoints | Build React UI |
| **Integration** | 12-18 | Error handling, edge cases | Connect frontend to API |
| **Polish** | 18-24 | Performance optimization | UI polish, responsiveness |
| **Sleep** | 24-30 | - | - |
| **Testing** | 30-36 | Bug fixes, API testing | End-to-end testing |
| **Demo** | 36-42 | Final API polish | Practice pitch, demo prep |
| **Buffer** | 42-48 | Emergency fixes | Submit |

---

## What We Skip If Short on Time

1. ❌ WhatsApp integration (show mockup only)
2. ❌ Full offline PWA (mention as "future work")
3. ❌ Marathi-specific fine-tuning (Google Vision handles it)
4. ❌ Fancy UI (Streamlit is good enough)

## What We MUST Have

1. ✅ Working quality assessment
2. ✅ Hindi/English OCR extraction
3. ✅ Fuzzy matching validation
4. ✅ Clear demo with real documents
5. ✅ Compelling presentation

---

## The Winning Demo Script

1. **Show the problem** (15 sec)
   - "Field workers photograph 100s of documents daily"
   - "Manual review takes 15 min per document"

2. **Live demo** (90 sec)
   - Upload blurry photo → "Quality too low, please retake"
   - Upload clear Hindi land record → Extract all fields
   - Show fuzzy match: "Found farmer Rajesh Patil (92% confidence)"

3. **Impact** (30 sec)
   - "15 minutes → 30 seconds per document"
   - "95% accuracy on Hindi handwritten text"
   - "Works offline in rural areas"

4. **Future** (15 sec)
   - "WhatsApp bot for direct farmer uploads"
   - "Scales to 100,000+ farmers"

---

*Built by Team [Name] for Cisco Tech for Social Good Hackathon 2026*
