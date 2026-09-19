"""
OCR service: preprocess label images with OpenCV/Pillow, then extract text
with Tesseract and parse known Legal Metrology label fields.
"""

import io
import os
import re

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance


class OCRService:
    def __init__(self):
        tess_cmd = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")
        if os.path.exists(tess_cmd):
            pytesseract.pytesseract.tesseract_cmd = tess_cmd

    # ------------------------------------------------------------------
    # Image pre-processing
    # ------------------------------------------------------------------

    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """
        Convert raw image bytes to a binary (thresholded + deskewed) numpy
        array suitable for Tesseract.
        """
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Enhance contrast and sharpness before converting to OpenCV
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = ImageEnhance.Sharpness(img).enhance(2.0)

        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Grayscale + Otsu threshold
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Deskew
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) > 10:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle += 90
            (h, w) = thresh.shape
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            thresh = cv2.warpAffine(
                thresh, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )

        return thresh

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def extract_text(self, image_bytes: bytes) -> str:
        """Return raw OCR text from pre-processed image bytes."""
        preprocessed = self.preprocess_image(image_bytes)
        # PSM 6 = assume a single uniform block of text
        custom_config = r"--oem 3 --psm 6 -l eng+hin"
        try:
            text = pytesseract.image_to_string(preprocessed, config=custom_config)
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError("Tesseract OCR is not installed on this service") from exc
        return text.strip()

    # ------------------------------------------------------------------
    # Field parsing
    # ------------------------------------------------------------------

    def extract_fields(self, raw_text: str) -> dict:
        """
        Parse well-known LM (PC) label fields from OCR output using regex
        patterns.  Returns a dict keyed by field name; only found fields are
        included.
        """
        patterns: dict[str, str] = {
            "manufacturer_name": (
                r"(?:Mfd\.|Manufactured\s+by|MFD\s+BY|Packed\s+by)"
                r"[:\s]+([^\n]{5,100})"
            ),
            "address": (
                r"(?:Address|Add\.)[:\s]+"
                r"([^\n]{5,200}(?:\n[^\n]{5,200})?)"
            ),
            "net_quantity": (
                r"(?:Net\s+(?:Qty|Weight|Content|Wt\.?)|Contents)"
                r"[:\s]+([^\n]{2,50})"
            ),
            "mrp": (
                r"(?:MRP|M\.R\.P\.)[:\s]*(?:Rs\.?|INR|₹)?\s*"
                r"([0-9][0-9,]*\.?\d*)"
            ),
            "mfr_date": (
                r"(?:Mfd\.|Mfg\.|Date\s+of\s+Mfg\.?|Manufactured\s+on)"
                r"[:\s]+([A-Za-z]{0,4}[/\-\s]?\d{2,4})"
            ),
            "best_before": (
                r"(?:Best\s+Before|BB|Use\s+by|Expiry|Exp\.?)"
                r"[:\s]+([^\n]{3,40})"
            ),
            "batch_no": (
                r"(?:Batch|Lot)\s*(?:No\.?|#)[:\s]+([A-Z0-9/\-]{2,20})"
            ),
            "fssai_no": (
                r"(?:FSSAI|FSSAI\s+Lic\.?\s*No\.?)[:\s]+([0-9]{14})"
            ),
            "customer_care": (
                r"(?:Customer\s+Care|Helpline|Toll[- ]Free|Consumer\s+Care)"
                r"[:\s]+([0-9\-\s\+]{7,20})"
            ),
            "country_of_origin": (
                r"(?:Country\s+of\s+Origin|Made\s+in|Product\s+of)"
                r"[:\s]+([A-Za-z ]{3,40})"
            ),
            "barcode": r"\b([0-9]{8,13})\b",
            "product_name": (
                r"^([A-Z][A-Za-z0-9 &\-]{3,80})$"
            ),
        }

        fields: dict[str, str] = {}
        for field, pattern in patterns.items():
            m = re.search(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
            if m:
                fields[field] = m.group(1).strip()

        return fields

    # ------------------------------------------------------------------
    # Combined pipeline
    # ------------------------------------------------------------------

    def process_image(self, image_bytes: bytes) -> dict:
        """
        Full pipeline: bytes -> OCR text -> structured fields.
        Returns {"raw_text": ..., "fields": {...}}.
        """
        preprocessed = self.preprocess_image(image_bytes)
        config = r"--oem 3 --psm 6 -l eng+hin"
        try:
            raw_text = pytesseract.image_to_string(preprocessed, config=config).strip()
            data = pytesseract.image_to_data(preprocessed, config=config, output_type=pytesseract.Output.DICT)
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError("Tesseract OCR is not installed on this service") from exc
        fields = self.extract_fields(raw_text)
        words = []
        confidences, heights = [], []
        for index, text in enumerate(data["text"]):
            confidence = float(data["conf"][index]) if str(data["conf"][index]) not in ("", "-1") else -1
            if text.strip() and confidence >= 0:
                confidences.append(confidence)
                heights.append(int(data["height"][index]))
                words.append({"text": text, "confidence": round(confidence, 1), "x": data["left"][index], "y": data["top"][index], "width": data["width"][index], "height": data["height"][index]})
        readability = round(sum(confidences) / len(confidences), 1) if confidences else 0.0
        analysis = {"readability_score": readability, "median_text_height_px": sorted(heights)[len(heights) // 2] if heights else 0, "word_boxes": words}
        return {"raw_text": raw_text, "fields": fields, "analysis": analysis}


ocr_service = OCRService()
