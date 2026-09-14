"""
OCR module stub.
Tesseract OCR has been deprecated and replaced with Diff-driven Paired-Crop VLM pipeline.
This module provides stub implementations for backwards compatibility without pytesseract dependencies.
"""

def ocr_region(gray_crop):
    """Deprecated stub: returns empty OCR result structure without running Tesseract."""
    return {
        "text": "",
        "confidence": 0.0,
        "word_count": 0,
        "psm": None
    }

