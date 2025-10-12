from PyPDF2 import PdfReader
from pathlib import Path

def extract_text_from_pdf(file_path):
    if isinstance(file_path, bytes):
        from io import BytesIO
        reader = PdfReader(BytesIO(file_path))
    else:
        reader = PdfReader(str(file_path))

    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text