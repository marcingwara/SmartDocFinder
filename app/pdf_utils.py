from PyPDF2 import PdfReader
from io import BytesIO
from pdf2image import convert_from_path, convert_from_bytes
import pytesseract
import chardet
import os

def extract_text_from_pdf(file_path_or_bytes):
    """Ekstrakcja tekstu z PDF z automatycznym rozpoznawaniem kodowania i fallbackiem OCR."""
    text_parts = []

    try:
        # --- 1️⃣ Najpierw spróbuj klasyczną ekstrakcję (PyPDF2)
        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            reader = PdfReader(BytesIO(file_path_or_bytes))
        else:
            reader = PdfReader(str(file_path_or_bytes))

        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                try:
                    detected = chardet.detect(page_text.encode("latin1", errors="ignore"))
                    encoding = detected.get("encoding", "utf-8") or "utf-8"
                    fixed = (
                        page_text
                        .encode("latin1", errors="ignore")
                        .decode(encoding, errors="ignore")
                        .replace("ﬁ", "fi")
                        .replace("ﬂ", "fl")
                    )
                except Exception:
                    fixed = page_text
                text_parts.append(fixed)

        text = " ".join(text_parts).strip()

        # --- 2️⃣ Jeśli PyPDF2 nic nie znalazł, zrób OCR
        if len(text) < 50:
            print("[OCR] PyPDF2 zwrócił zbyt mało tekstu – uruchamiam OCR...")
            if isinstance(file_path_or_bytes, (bytes, bytearray)):
                images = convert_from_bytes(file_path_or_bytes)
            else:
                images = convert_from_path(str(file_path_or_bytes))

            ocr_text = []
            for img in images:
                page_text = pytesseract.image_to_string(img, lang="pol+eng")
                ocr_text.append(page_text)

            text = "\n".join(ocr_text).strip()
            print(f"[OCR] Zidentyfikowano {len(text)} znaków po OCR")

        # --- 3️⃣ Finalne czyszczenie
        text = " ".join(text.split())
        return text

    except Exception as e:
        print(f"[PDF] Error extracting text: {e}")
        return ""