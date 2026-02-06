"""
Quality Assessment Module
Checks photo quality before OCR processing.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List


@dataclass
class QualityReport:
    is_acceptable: bool
    blur_score: float      # 0-100, higher = sharper
    brightness_score: float # 0-100, 50 = optimal
    glare_score: float     # 0-100, higher = less glare
    angle_score: float     # 0-100, higher = more straight
    resolution_ok: bool
    issues: List[str]
    suggestions: List[str]


def assess_quality(image_path: str, min_blur_threshold: float = 30) -> QualityReport:
    """
    Assess the quality of a document image.
    
    Args:
        image_path: Path to the image file
        min_blur_threshold: Minimum acceptable blur score (0-100)
    
    Returns:
        QualityReport with scores and recommendations
    """
    img = cv2.imread(image_path)
    if img is None:
        return QualityReport(
            is_acceptable=False,
            blur_score=0,
            brightness_score=0,
            glare_score=0,
            angle_score=0,
            resolution_ok=False,
            issues=["Could not read image file"],
            suggestions=["Please upload a valid JPG or PNG image"]
        )
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = img.shape[:2]
    
    issues = []
    suggestions = []
    
    # 1. Blur Detection (Laplacian variance)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    blur_score = min(100, laplacian_var / 5)  # Normalize to 0-100
    
    if blur_score < min_blur_threshold:
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
    glare_score = max(0, 100 - glare_percentage * 10)
    
    if glare_percentage > 5:
        issues.append("Glare detected on document")
        suggestions.append("Tilt document to avoid reflections")
    
    # 4. Resolution Check
    resolution_ok = width >= 800 and height >= 600
    
    if not resolution_ok:
        issues.append(f"Resolution too low ({width}x{height})")
        suggestions.append("Move closer to document or use higher camera quality")
    
    # 5. Angle/Skew Detection (Hough transform)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
    angle_score = 100  # Assume good
    
    if lines is not None and len(lines) > 0:
        angles = [line[0][1] * 180 / np.pi for line in lines[:10]]
        avg_angle = np.mean(angles)
        skew = abs(90 - avg_angle) if avg_angle > 45 else abs(avg_angle)
        
        if skew > 10:
            angle_score = max(0, 100 - skew * 5)
            issues.append(f"Document is tilted ({skew:.1f}°)")
            suggestions.append("Align document edges with camera frame")
    
    # Determine acceptability
    is_acceptable = (
        blur_score >= min_blur_threshold and
        resolution_ok and
        glare_score > 50 and
        len(issues) <= 2  # Allow minor issues
    )
    
    return QualityReport(
        is_acceptable=is_acceptable,
        blur_score=round(blur_score, 1),
        brightness_score=round(brightness_score, 1),
        glare_score=round(glare_score, 1),
        angle_score=round(angle_score, 1),
        resolution_ok=resolution_ok,
        issues=issues,
        suggestions=suggestions if not is_acceptable else []
    )


def preprocess_image(image_path: str, output_path: str = None) -> str:
    """
    Preprocess image for better OCR results.
    
    Args:
        image_path: Path to input image
        output_path: Path for processed image (optional)
    
    Returns:
        Path to processed image
    """
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Increase contrast using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # Binarization (adaptive threshold)
    binary = cv2.adaptiveThreshold(
        enhanced, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Save
    if output_path is None:
        output_path = image_path.replace('.', '_processed.')
    
    cv2.imwrite(output_path, binary)
    return output_path


if __name__ == "__main__":
    # Test with sample image
    import sys
    if len(sys.argv) > 1:
        report = assess_quality(sys.argv[1])
        print(f"Acceptable: {report.is_acceptable}")
        print(f"Blur Score: {report.blur_score}")
        print(f"Issues: {report.issues}")
        print(f"Suggestions: {report.suggestions}")
