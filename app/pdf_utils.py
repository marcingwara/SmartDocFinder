from PyPDF2 import PdfReader
from pathlib import Path
from io import BytesIO

def extract_text_from_pdf(file_path_or_bytes):
    try:
        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            reader = PdfReader(BytesIO(file_path_or_bytes))
        else:
            reader = PdfReader(str(file_path_or_bytes))
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text)
    except Exception as e:
        # fail gracefully
        return ""