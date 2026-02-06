"""
Farmers for Forests - Document Verification API
Main FastAPI application.
"""

import os
import tempfile
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from quality_assessment import assess_quality, QualityReport
from ocr_pipeline import OCRPipeline, OCRResult
from validation_engine import ValidationEngine, ValidationResult

# Configuration
USE_GOOGLE_VISION = os.getenv("USE_GOOGLE_VISION", "false").lower() == "true"
FARMER_DB_PATH = os.getenv("FARMER_DB_PATH", "data/farmers.json")

# Initialize FastAPI
app = FastAPI(
    title="Farmers for Forests - Document Verification",
    description="AI-powered document verification for farmer onboarding. Supports Hindi, Marathi, and English.",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components (lazy loading)
_ocr = None
_validator = None

def get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = OCRPipeline(use_google_vision=USE_GOOGLE_VISION)
    return _ocr

def get_validator():
    global _validator
    if _validator is None:
        db_path = Path(__file__).parent.parent / FARMER_DB_PATH
        if db_path.exists():
            _validator = ValidationEngine(str(db_path))
        else:
            # Use sample data if no database
            _validator = ValidationEngine([
                {
                    "id": "DEMO001",
                    "name": "राजेश कुमार पाटिल",
                    "name_en": "Rajesh Kumar Patil",
                    "account_number": "12345678901234",
                    "ifsc_code": "SBIN0001234"
                }
            ])
    return _validator


# Response Models
class QualityResponse(BaseModel):
    is_acceptable: bool
    blur_score: float
    brightness_score: float
    glare_score: float
    angle_score: float
    resolution_ok: bool
    issues: List[str]
    suggestions: List[str]

class OCRResponse(BaseModel):
    raw_text: str
    detected_language: str
    confidence: float
    fields: dict
    ocr_engine: str

class ValidationResponse(BaseModel):
    is_valid: bool
    confidence: float
    matched_farmer: Optional[dict]
    field_matches: dict
    issues: List[str]
    warnings: List[str]

class VerificationResponse(BaseModel):
    success: bool
    quality: QualityResponse
    ocr_result: Optional[OCRResponse]
    validation: Optional[ValidationResponse]
    summary: str
    next_steps: List[str]


@app.get("/")
async def root():
    """Health check and API info."""
    return {
        "name": "Farmers for Forests - Document Verification API",
        "version": "1.0.0",
        "status": "healthy",
        "ocr_engine": "google_vision" if USE_GOOGLE_VISION else "tesseract",
        "endpoints": {
            "/verify": "POST - Full document verification",
            "/quality": "POST - Quality assessment only",
            "/ocr": "POST - OCR extraction only",
            "/validate": "POST - Validation only (JSON input)"
        }
    }


@app.post("/verify", response_model=VerificationResponse)
async def verify_document(file: UploadFile = File(...)):
    """
    Full document verification pipeline.
    
    Steps:
    1. Quality assessment
    2. OCR extraction
    3. Field validation
    
    Returns comprehensive verification result.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (jpg, png)")
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Step 1: Quality Assessment
        quality = assess_quality(tmp_path)
        quality_response = QualityResponse(**quality.__dict__)
        
        if not quality.is_acceptable:
            return VerificationResponse(
                success=False,
                quality=quality_response,
                ocr_result=None,
                validation=None,
                summary="📷 Document quality insufficient for processing.",
                next_steps=quality.suggestions or ["Please retake the photo with better lighting and focus"]
            )
        
        # Step 2: OCR Extraction
        try:
            ocr = get_ocr()
            ocr_result = ocr.extract_text(tmp_path)
        except Exception as e:
            return VerificationResponse(
                success=False,
                quality=quality_response,
                ocr_result=None,
                validation=None,
                summary=f"❌ OCR processing failed: {str(e)}",
                next_steps=["Please try again or contact support"]
            )
        
        ocr_response = OCRResponse(
            raw_text=ocr_result.raw_text[:1000],  # Truncate for response
            detected_language=ocr_result.detected_language,
            confidence=ocr_result.confidence,
            fields=ocr_result.extracted_fields,
            ocr_engine=ocr_result.ocr_engine
        )
        
        # Check if any fields were extracted
        fields = ocr_result.extracted_fields
        if not any(fields.values()):
            return VerificationResponse(
                success=False,
                quality=quality_response,
                ocr_result=ocr_response,
                validation=None,
                summary="⚠️ Could not extract any fields from document.",
                next_steps=[
                    "Ensure document contains visible name, account number, or land details",
                    "Try uploading a clearer image"
                ]
            )
        
        # Step 3: Validation
        validator = get_validator()
        validation = validator.validate(fields)
        
        validation_response = ValidationResponse(
            is_valid=validation.is_valid,
            confidence=validation.confidence,
            matched_farmer=_sanitize_farmer(validation.matched_farmer),
            field_matches=validation.field_matches,
            issues=validation.issues,
            warnings=validation.warnings
        )
        
        # Build summary
        if validation.is_valid:
            farmer_name = validation.matched_farmer.get('name_en') or validation.matched_farmer.get('name', 'Unknown')
            summary = f"✅ Document verified! Matched farmer: {farmer_name}"
            next_steps = ["Document ready for processing", "No further action required"]
        else:
            summary = f"⚠️ Document needs review. {len(validation.issues)} issue(s) found."
            next_steps = validation.issues + ["Please verify and re-upload if needed"]
        
        return VerificationResponse(
            success=validation.is_valid,
            quality=quality_response,
            ocr_result=ocr_response,
            validation=validation_response,
            summary=summary,
            next_steps=next_steps
        )
    
    finally:
        # Cleanup
        try:
            os.unlink(tmp_path)
        except:
            pass


@app.post("/quality")
async def check_quality(file: UploadFile = File(...)):
    """Check document quality only (no OCR)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        quality = assess_quality(tmp_path)
        return quality.__dict__
    finally:
        os.unlink(tmp_path)


@app.post("/ocr")
async def extract_text(file: UploadFile = File(...)):
    """Run OCR only (no validation)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        ocr = get_ocr()
        result = ocr.extract_text(tmp_path)
        return {
            "raw_text": result.raw_text,
            "language": result.detected_language,
            "confidence": result.confidence,
            "fields": result.extracted_fields,
            "engine": result.ocr_engine
        }
    finally:
        os.unlink(tmp_path)


class ValidateRequest(BaseModel):
    name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    aadhaar: Optional[str] = None
    survey_number: Optional[str] = None
    phone: Optional[str] = None

@app.post("/validate")
async def validate_fields(request: ValidateRequest):
    """Validate extracted fields against database (JSON input)."""
    validator = get_validator()
    fields = request.dict(exclude_none=True)
    
    if not fields:
        raise HTTPException(400, "At least one field must be provided")
    
    result = validator.validate(fields)
    return {
        "is_valid": result.is_valid,
        "confidence": result.confidence,
        "matched_farmer": _sanitize_farmer(result.matched_farmer),
        "field_matches": result.field_matches,
        "issues": result.issues,
        "warnings": result.warnings
    }


def _sanitize_farmer(farmer: Optional[dict]) -> Optional[dict]:
    """Remove sensitive fields from farmer record for response."""
    if not farmer:
        return None
    
    # Return only safe fields
    safe_fields = ['id', 'name', 'name_en', 'village', 'district', 'state']
    return {k: v for k, v in farmer.items() if k in safe_fields}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
