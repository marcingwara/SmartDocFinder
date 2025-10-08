from PyPDF2 import PdfReader
from io import BytesIO
from pathlib import Path
from typing import Union

def extract_text_from_pdf(source: Union[bytes, bytearray, str, Path]) -> str:
    """
    Accepts:
      - bytes (file content)
      - Path or str (file path)
    Returns extracted text (empty string on error).
    """
    try:
        if isinstance(source, (bytes, bytearray)):
            reader = PdfReader(BytesIO(source))
        else:
            p = Path(source)
            data = p.read_bytes()
            reader = PdfReader(BytesIO(data))

        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except Exception:
        return ""