from app.vertex_utils import summarize_text
from app.pdf_utils import extract_text_from_pdf
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

def analyze_pdf(path_or_bytes) -> str:
    """
    Generate a meaningful summary for the document using Vertex AI if available,
    otherwise a keyword-based local summary.
    """
    try:
        # Extract text
        if isinstance(path_or_bytes, (bytes, bytearray)):
            text = path_or_bytes.decode('utf-8', errors='ignore')
        else:
            text = extract_text_from_pdf(path_or_bytes)

        if not text or len(text.strip()) == 0:
            return "Brak treści w pliku PDF."

        text = text.replace("\n", " ").strip()
        text = re.sub(r"\s+", " ", text)
        text = text[:15000]

        # === 1️⃣ Vertex AI Summary ===
        summary = summarize_text(text)
        if summary and summary.strip():
            return summary.strip()

        # === 2️⃣ Local fallback: keyword-based ===
        words = re.findall(r"\b\w{5,}\b", text.lower())  # słowa dłuższe niż 4 znaki
        common = [w for w, _ in Counter(words).most_common(10)]
        keywords = ", ".join(common[:7])

        sentences = re.split(r'(?<=[.!?])\s+', text)
        middle_section = sentences[len(sentences)//3 : len(sentences)//3 + 3]
        preview = " ".join(middle_section)

        summary_text = (
            f"Dokument dotyczy głównie tematów takich jak: {keywords}. "
            f"Zawiera analizę i opis kluczowych zagadnień, takich jak "
            f"{common[0] if common else 'temat główny'}. "
            f"Omawia także: {preview[:400].strip()}..."
        )

        return summary_text

    except Exception as e:
        logger.error(f"[AI] Error analyzing PDF: {e}")
        return "Błąd generowania streszczenia."