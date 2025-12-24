import json
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path

# -----------------------------
# CONFIG
# -----------------------------
PDF_PATH = "input.pdf"
OUTPUT_JSON = "raw_ocr_output.json"

DPI = 400  # high DPI = better OCR
TESSERACT_CONFIG = r"""
--oem 1
--psm 4
-preserve_interword_spaces 1
"""

# If language packs are available, ADD them
# Example: lang="eng+hin"
OCR_LANG = "eng+mar"

# -----------------------------
# IMAGE PREPROCESSING
# -----------------------------
def preprocess_image(pil_img):
    """
    Conservative preprocessing for scanned documents.
    Avoids over-aggressive operations that destroy characters.
    """
    img = np.array(pil_img)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise slightly (preserves edges)
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # Adaptive thresholding (handles uneven lighting)
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=11
    )

    return thresh


# -----------------------------
# OCR PER PAGE
# -----------------------------
def ocr_page(image):
    return pytesseract.image_to_string(
        image,
        lang=OCR_LANG,
        config=TESSERACT_CONFIG
    )


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def extract_raw_ocr(pdf_path):
    pages = convert_from_path(pdf_path, dpi=DPI, poppler_path = "D:\\poppler-25.12.0\\Library\\bin", fmt="png", use_pdftocairo = True)
    ocr_results = {}

    for idx, page in enumerate(pages, start=1):
        print(f"OCRing page {idx}...")

        processed = preprocess_image(page)
        text = ocr_page(processed)

        # Store raw text exactly as produced
        ocr_results[str(idx)] = text

    return ocr_results


if __name__ == "__main__":
    pdf_path = Path(PDF_PATH)
    assert pdf_path.exists(), "PDF not found"

    raw_text_by_page = extract_raw_ocr(pdf_path)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(
            raw_text_by_page,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"\nOCR extraction complete → {OUTPUT_JSON}")
