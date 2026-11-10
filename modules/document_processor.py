
from pathlib import Path
import io
import pymupdf as fitz
import pytesseract

from PIL import Image


# Windows Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_pdf_text(file_path: str) -> dict:
    """
    Extract text page by page from machine-readable
    and scanned PDFs using PyMuPDF and Tesseract OCR.
    """

    path = Path(file_path)

    if not path.exists():
        return {
            "success": False,
            "filename": path.name,
            "text": "",
            "pages": 0,
            "page_results": [],
            "error": "File not found",
            "needs_ocr": False,
            "ocr_used": False
        }

    if path.suffix.lower() != ".pdf":
        return {
            "success": False,
            "filename": path.name,
            "text": "",
            "pages": 0,
            "page_results": [],
            "error": "Only PDF files are supported",
            "needs_ocr": False,
            "ocr_used": False
        }

    try:
        page_results = []
        ocr_used = False

        with fitz.open(path) as document:

            total_pages = len(document)

            for page_number, page in enumerate(document, start=1):

                # STEP 1: Extract normal PDF text
                page_text = page.get_text("text").strip()

                page_ocr_used = False

                # STEP 2: Run OCR if page has insufficient text
                if len(page_text) < 30:

                    page_ocr_used = True
                    ocr_used = True

                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(2, 2),
                        alpha=False
                    )

                    image = Image.open(
                        io.BytesIO(pix.tobytes("png"))
                    )

                    page_text = pytesseract.image_to_string(
                        image,
                        lang="eng"
                    ).strip()

                page_results.append({
                    "page_number": page_number,
                    "text": page_text,
                    "success": bool(page_text),
                    "ocr_used": page_ocr_used,
                    "document_type": None
                })

        # STEP 3: Combine text for backward compatibility
        combined_text = "\n\n".join(
            f"PAGE {item['page_number']}\n{item['text']}"
            for item in page_results
            if item["text"]
        ).strip()

        if not combined_text:

            return {
                "success": False,
                "filename": path.name,
                "text": "",
                "pages": total_pages,
                "page_results": page_results,
                "error": "No readable text found, even after OCR",
                "needs_ocr": True,
                "ocr_used": ocr_used
            }

        return {
            "success": True,
            "filename": path.name,
            "text": combined_text,
            "pages": total_pages,
            "page_results": page_results,
            "error": None,
            "needs_ocr": False,
            "ocr_used": ocr_used
        }

    except Exception as exc:

        return {
            "success": False,
            "filename": path.name,
            "text": "",
            "pages": 0,
            "page_results": [],
            "error": str(exc),
            "needs_ocr": False,
            "ocr_used": False
        }


def extract_documents(document_paths: list) -> list:
    """Process all uploaded PDF documents."""

    results = []

    for file_path in document_paths:
        results.append(extract_pdf_text(file_path))

    return results
