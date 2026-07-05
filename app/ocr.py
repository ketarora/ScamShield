"""
Extracts text from forwarded screenshots. Tesseract is free and good
enough for clean screenshots -- only swap for a cloud OCR API later if
accuracy on real-world blurry forwards turns out to actually be a problem.
"""
import io
import logging

import pytesseract
from PIL import Image

logger = logging.getLogger("scamshield.ocr")


def extract_text_from_image(image_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception:
        logger.exception("OCR failed")
        return ""
