from PyPDF2 import PdfReader
from io import BytesIO
from pdf2image import convert_from_path, convert_from_bytes
import pytesseract
import chardet
import os
import re
from tempfile import NamedTemporaryFile

def extract_text_from_pdf(file_path_or_bytes):
    """
    Ekstrakcja tekstu z PDF z automatycznym rozpoznawaniem kodowania i fallbackiem OCR.
    Obsługuje pliki binarne (bytes) i ścieżki do plików.
    """
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
            text = extract_text_with_ocr(file_path_or_bytes)

        # --- 3️⃣ Finalne czyszczenie
        text = _clean_text(text)
        print(f"[PDF] Extracted {len(text)} characters total.")
        return text

    except Exception as e:
        print(f"[PDF] ❌ Error extracting text: {e}")
        try:
            # Fallback OCR jako ostateczne rozwiązanie
            text = extract_text_with_ocr(file_path_or_bytes)
            return _clean_text(text)
        except Exception as ocr_err:
            print(f"[PDF] ❌ OCR fallback failed: {ocr_err}")
            return ""


def extract_text_with_ocr(file_path_or_bytes):
    """
    OCR fallback: renderuje strony PDF do obrazów i rozpoznaje tekst (polski + angielski).
    """
    try:
        # Obsługa zarówno plików bytes, jak i ścieżek
        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            images = convert_from_bytes(file_path_or_bytes, dpi=200)
        else:
            images = convert_from_path(str(file_path_or_bytes), dpi=200)

        ocr_texts = []
        for i, img in enumerate(images):
            page_text = pytesseract.image_to_string(img, lang="pol+eng")
            page_text = _clean_text(page_text)
            ocr_texts.append(page_text)
            print(f"[OCR] ✅ Page {i+1}: {len(page_text)} chars")

        full_text = "\n".join(ocr_texts).strip()
        print(f"[OCR] Zidentyfikowano {len(full_text)} znaków po OCR.")
        return full_text

    except Exception as e:
        print(f"[OCR] ❌ OCR extraction failed: {e}")
        return ""


def _clean_text(t: str) -> str:
    """
    Czyści tekst z nadmiarowych spacji, znaków specjalnych i łączy słowa.
    """
    try:
        t = t.replace("\r", " ").replace("\n", " ")
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"[^\x00-\x7FĄąĆćĘęŁłŃńÓóŚśŹźŻż ]+", "", t)  # usuń nietypowe znaki
        return t
    except Exception:
        return t.strip()