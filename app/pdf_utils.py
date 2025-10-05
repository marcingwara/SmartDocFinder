from PyPDF2 import PdfReader
from io import BytesIO
from pathlib import Path
from typing import Union
import logging

logger = logging.getLogger(__name__)

def extract_text_from_pdf(input_data: Union[bytes, str, Path]) -> str:
    """
    Accepts:
      - bytes (raw file bytes)
      - path (str or Path) to local PDF file
    Returns extracted text (concatenation of pages). Robust to common errors.
    """
    reader = None
    try:
        if isinstance(input_data, (bytes, bytearray)):
            f = BytesIO(input_data)
            reader = PdfReader(f)
        else:
            # treat as path
            path = Path(input_data)
            with open(path, "rb") as fh:
                reader = PdfReader(fh)
        text_parts = []
        for p in reader.pages:
            page_text = p.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.exception("Failed extracting PDF text: %s", e)
        # return empty string on failure, but log error
        return ""