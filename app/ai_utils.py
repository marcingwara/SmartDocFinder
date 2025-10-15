from app.vertex_utils import generate_embedding, summarize_text
import logging

logger = logging.getLogger(__name__)

def analyze_pdf(path_or_bytes) -> str:
    """
    Return a short summary (string). This function tries Vertex; on failure returns empty string.
    """
    try:
        # extract_text should be called by caller if needed; we'll accept either bytes or path
        if isinstance(path_or_bytes, (bytes, bytearray)):
            text = path_or_bytes.decode('utf-8', errors='ignore')[:20000]
        else:
            # path passed — read text externally (the route uses pdf_utils.extract_text_from_pdf)
            from app.pdf_utils import extract_text_from_pdf
            text = extract_text_from_pdf(path_or_bytes)[:20000]

        if not text:
            return ""

        summary = summarize_text(text)
        if not summary:
            # fallback simple heuristic: first 300 chars
            return (text[:300] + "...") if len(text) > 300 else text
        return summary
    except Exception as e:
        logger.exception("AI analysis failed: %s", e)
        return ""