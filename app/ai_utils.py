from pathlib import Path
from app.pdf_utils import extract_text_from_pdf

def analyze_pdf(file_path: Path) -> str:
    try:
        text = extract_text_from_pdf(file_path)
        return text[:500]
    except Exception:
        return ""