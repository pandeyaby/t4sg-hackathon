"""
OCR Pipeline Module
Extracts text from documents in Hindi, Marathi, and English.
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict
from pathlib import Path

# Conditional imports for flexibility
try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class OCRResult:
    raw_text: str
    detected_language: str
    confidence: float
    extracted_fields: Dict
    ocr_engine: str


class OCRPipeline:
    """
    Multi-language OCR pipeline supporting Hindi, Marathi, and English.
    Uses Google Vision API as primary, Tesseract as fallback.
    """
    
    def __init__(self, use_google_vision: bool = True):
        self.use_google_vision = use_google_vision and GOOGLE_VISION_AVAILABLE
        
        if self.use_google_vision:
            self.client = vision.ImageAnnotatorClient()
        elif not TESSERACT_AVAILABLE:
            raise RuntimeError("No OCR engine available. Install google-cloud-vision or pytesseract.")
    
    def extract_text(self, image_path: str) -> OCRResult:
        """
        Extract text from document image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            OCRResult with extracted text and fields
        """
        if self.use_google_vision:
            return self._google_vision_ocr(image_path)
        else:
            return self._tesseract_ocr(image_path)
    
    def _google_vision_ocr(self, image_path: str) -> OCRResult:
        """Use Google Cloud Vision API for OCR."""
        with open(image_path, 'rb') as f:
            content = f.read()
        
        image = vision.Image(content=content)
        
        # Use document_text_detection for better structured output
        response = self.client.document_text_detection(
            image=image,
            image_context={"language_hints": ["hi", "mr", "en"]}
        )
        
        if response.error.message:
            raise RuntimeError(f"Google Vision error: {response.error.message}")
        
        text = response.full_text_annotation.text if response.full_text_annotation else ""
        
        # Detect primary language
        lang = self._detect_language(text)
        
        # Extract structured fields
        fields = self._extract_fields(text, lang)
        
        # Calculate confidence from page-level confidence
        confidence = 0.9  # Default high for Google Vision
        if response.full_text_annotation.pages:
            page = response.full_text_annotation.pages[0]
            if page.confidence:
                confidence = page.confidence
        
        return OCRResult(
            raw_text=text,
            detected_language=lang,
            confidence=confidence,
            extracted_fields=fields,
            ocr_engine="google_vision"
        )
    
    def _tesseract_ocr(self, image_path: str) -> OCRResult:
        """Use Tesseract for OCR (offline fallback)."""
        img = Image.open(image_path)
        
        # Try with Hindi + English
        try:
            text = pytesseract.image_to_string(img, lang='hin+eng')
        except pytesseract.TesseractError:
            # Fallback to English only
            text = pytesseract.image_to_string(img, lang='eng')
        
        lang = self._detect_language(text)
        fields = self._extract_fields(text, lang)
        
        # Get confidence from Tesseract data
        try:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.5
        except:
            confidence = 0.6
        
        return OCRResult(
            raw_text=text,
            detected_language=lang,
            confidence=confidence,
            extracted_fields=fields,
            ocr_engine="tesseract"
        )
    
    def _detect_language(self, text: str) -> str:
        """Detect primary language from text."""
        # Check for Devanagari script (Hindi/Marathi)
        devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
        total_alpha = sum(1 for c in text if c.isalpha())
        
        if total_alpha == 0:
            return "unknown"
        
        devanagari_ratio = devanagari_chars / total_alpha
        
        if devanagari_ratio > 0.3:
            # Could be Hindi or Marathi - check for Marathi-specific words
            marathi_markers = ['आहे', 'नाही', 'होते', 'असे', 'करणे']
            if any(marker in text for marker in marathi_markers):
                return "mr"  # Marathi
            return "hi"  # Hindi
        
        return "en"  # English
    
    def _extract_fields(self, text: str, lang: str) -> Dict:
        """
        Extract key fields from document text.
        
        Looks for:
        - Name
        - Account number
        - IFSC code
        - Aadhaar number
        - Survey/Khasra number
        - Area (acres/hectares)
        - Address
        """
        fields = {
            "name": None,
            "account_number": None,
            "ifsc_code": None,
            "aadhaar": None,
            "survey_number": None,
            "area": None,
            "address": None,
            "phone": None
        }
        
        # Normalize text
        text_normalized = text.replace('\n', ' ').strip()
        
        # Account number (10-18 digits, not starting with 0)
        acc_patterns = [
            r'(?:a/?c|account|खाता)\s*(?:no\.?|number|नं\.?)?\s*:?\s*(\d{10,18})',
            r'\b([1-9]\d{9,17})\b'
        ]
        for pattern in acc_patterns:
            match = re.search(pattern, text_normalized, re.I)
            if match:
                fields["account_number"] = match.group(1)
                break
        
        # IFSC code (4 letters + 0 + 6 alphanumeric)
        ifsc_match = re.search(r'\b([A-Z]{4}0[A-Z0-9]{6})\b', text_normalized)
        if ifsc_match:
            fields["ifsc_code"] = ifsc_match.group(1)
        
        # Aadhaar (12 digits, often with spaces)
        aadhaar_patterns = [
            r'(?:aadhaar|आधार)\s*:?\s*(\d{4}\s?\d{4}\s?\d{4})',
            r'\b(\d{4}\s?\d{4}\s?\d{4})\b'
        ]
        for pattern in aadhaar_patterns:
            match = re.search(pattern, text_normalized, re.I)
            if match:
                aadhaar = match.group(1).replace(" ", "")
                if len(aadhaar) == 12:
                    fields["aadhaar"] = aadhaar
                    break
        
        # Survey/Khasra number
        survey_patterns = [
            r'(?:survey|khasra|खसरा|सर्वे|गट)\s*(?:no\.?|number|नं\.?|क्र\.?)?\s*:?\s*([0-9]+[\/\-]?[A-Za-z0-9]*)',
            r'(?:plot|प्लॉट)\s*(?:no\.?)?\s*:?\s*([0-9]+[\/\-]?[A-Za-z0-9]*)'
        ]
        for pattern in survey_patterns:
            match = re.search(pattern, text_normalized, re.I)
            if match:
                fields["survey_number"] = match.group(1)
                break
        
        # Area in acres/hectares
        area_patterns = [
            r'(\d+\.?\d*)\s*(acres?|hectares?|एकड़|हेक्टेयर|गुंठे|आर)',
            r'(?:area|क्षेत्र)\s*:?\s*(\d+\.?\d*)\s*(acres?|hectares?|एकड़|हेक्टेयर)?'
        ]
        for pattern in area_patterns:
            match = re.search(pattern, text_normalized, re.I)
            if match:
                area_value = match.group(1)
                area_unit = match.group(2) if len(match.groups()) > 1 else "units"
                fields["area"] = f"{area_value} {area_unit or 'units'}"
                break
        
        # Phone number (Indian format)
        phone_match = re.search(r'(?:\+91|91)?[- ]?([6-9]\d{9})\b', text_normalized)
        if phone_match:
            fields["phone"] = phone_match.group(1)
        
        # Name extraction (heuristic - look for common patterns)
        name_patterns = [
            r'(?:name|नाम|नांव)\s*:?\s*([^\n,\d]{3,50})',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})'  # English name at start
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.I | re.M)
            if match:
                name = match.group(1).strip()
                # Filter out common non-name words
                if not any(word in name.lower() for word in ['bank', 'account', 'ifsc', 'branch']):
                    fields["name"] = name
                    break
        
        return fields


# Convenience function for direct use
def extract_document_text(image_path: str, use_google: bool = True) -> OCRResult:
    """
    Convenience function to extract text from a document image.
    
    Args:
        image_path: Path to image
        use_google: Whether to use Google Vision (requires API key)
    
    Returns:
        OCRResult with extracted text and fields
    """
    pipeline = OCRPipeline(use_google_vision=use_google)
    return pipeline.extract_text(image_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = extract_document_text(sys.argv[1], use_google=False)
        print(f"Language: {result.detected_language}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Fields: {result.extracted_fields}")
        print(f"\nRaw text:\n{result.raw_text[:500]}...")
