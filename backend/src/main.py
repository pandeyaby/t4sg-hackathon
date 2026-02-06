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
from db import (
    init_db,
    list_farmers,
    get_farmer,
    create_farmer,
    update_farmer,
    delete_farmer,
    get_profile,
    upsert_profile,
    delete_profile,
    list_documents,
    get_document,
    create_document,
    update_document,
    delete_document,
)

# Configuration
USE_GOOGLE_VISION = os.getenv("USE_GOOGLE_VISION", "false").lower() == "true"
USE_TESSERACT = os.getenv("USE_TESSERACT", "false").lower() == "true"
USE_TESSERACT_CLI = os.getenv("USE_TESSERACT_CLI", "false").lower() == "true"
FARMER_DB_PATH = os.getenv("FARMER_DB_PATH", "data/farmers.db")

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
        _ocr = OCRPipeline(
            use_google_vision=USE_GOOGLE_VISION,
            allow_tesseract=USE_TESSERACT,
            allow_tesseract_cli=USE_TESSERACT_CLI,
        )
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


@app.on_event("startup")
def on_startup():
    db_path = Path(__file__).parent.parent / FARMER_DB_PATH
    init_db(str(db_path))


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


class FarmerBase(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    phone: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    survey_number: Optional[str] = None
    area_acres: Optional[float] = None
    enrolled_date: Optional[str] = None


class FarmerCreate(FarmerBase):
    id: str


class FarmerUpdate(FarmerBase):
    pass


class ProfileUpsert(BaseModel):
    farmer_id: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    offline_enabled: bool = False


class DocumentCreate(BaseModel):
    farmer_id: str
    filename: str
    status: str = "pending"
    metadata: Optional[dict] = None


class DocumentUpdate(BaseModel):
    status: Optional[str] = None
    metadata: Optional[dict] = None


@app.get("/farmers")
def api_list_farmers():
    return list_farmers()


@app.get("/farmers/{farmer_id}")
def api_get_farmer(farmer_id: str):
    farmer = get_farmer(farmer_id)
    if not farmer:
        raise HTTPException(404, "Farmer not found")
    return farmer


@app.post("/farmers")
def api_create_farmer(payload: FarmerCreate):
    created = create_farmer(payload.dict())
    return created


@app.put("/farmers/{farmer_id}")
def api_update_farmer(farmer_id: str, payload: FarmerUpdate):
    updated = update_farmer(farmer_id, payload.dict(exclude_none=True))
    if not updated:
        raise HTTPException(404, "Farmer not found")
    return updated


@app.delete("/farmers/{farmer_id}")
def api_delete_farmer(farmer_id: str):
    if not delete_farmer(farmer_id):
        raise HTTPException(404, "Farmer not found")
    return {"deleted": True}


@app.get("/profiles/{farmer_id}")
def api_get_profile(farmer_id: str):
    profile = get_profile(farmer_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile


@app.post("/profiles")
def api_upsert_profile(payload: ProfileUpsert):
    return upsert_profile(payload.dict())


@app.delete("/profiles/{farmer_id}")
def api_delete_profile(farmer_id: str):
    if not delete_profile(farmer_id):
        raise HTTPException(404, "Profile not found")
    return {"deleted": True}


@app.get("/documents")
def api_list_documents(farmer_id: Optional[str] = None):
    return list_documents(farmer_id)


@app.get("/documents/{doc_id}")
def api_get_document(doc_id: int):
    document = get_document(doc_id)
    if not document:
        raise HTTPException(404, "Document not found")
    return document


@app.post("/documents")
def api_create_document(payload: DocumentCreate):
    return create_document(payload.dict())


@app.put("/documents/{doc_id}")
def api_update_document(doc_id: int, payload: DocumentUpdate):
    updated = update_document(doc_id, payload.dict(exclude_none=True))
    if not updated:
        raise HTTPException(404, "Document not found")
    return updated


@app.delete("/documents/{doc_id}")
def api_delete_document(doc_id: int):
    if not delete_document(doc_id):
        raise HTTPException(404, "Document not found")
    return {"deleted": True}


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
        
        # Build summary and next steps
        if validation.is_valid:
            farmer_name = validation.matched_farmer.get('name_en') or validation.matched_farmer.get('name', 'Unknown')
            summary = f"✅ Document verified! Matched farmer: {farmer_name}"
        else:
            summary = f"⚠️ Document needs review. {len(validation.issues)} issue(s) found."

        next_steps = _build_next_steps(quality_response, ocr_response, validation)
        
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


def _build_next_steps(
    quality: QualityResponse,
    ocr_result: Optional[OCRResponse],
    validation: ValidationResult
) -> List[str]:
    steps: List[str] = []

    if not quality.is_acceptable:
        if quality.suggestions:
            steps.extend(quality.suggestions)
        steps.append("Retake photo in good light and ensure all edges are visible")
        return steps

    if not ocr_result:
        steps.append("Retry OCR after improving image clarity")
        steps.append("If OCR keeps failing, capture a higher-resolution image")
        return steps

    missing_fields = [
        field for field, value in ocr_result.fields.items()
        if field in {"name", "account_number", "ifsc_code", "survey_number"} and not value
    ]
    if missing_fields:
        steps.append(f"Ensure these fields are clearly visible: {', '.join(missing_fields)}")

    if validation.is_valid:
        steps.append("Proceed to enrollment and mark document as verified")
        steps.append("Notify the field worker and archive the verified document")
        return steps

    if validation.warnings:
        steps.append("Manual review recommended due to low confidence match")

    if validation.issues:
        steps.append("Resolve validation issues and re-upload the corrected document")
    else:
        steps.append("Please verify and re-upload if needed")

    steps.append("If mismatch persists, cross-check with the farmer record")
    return steps


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
