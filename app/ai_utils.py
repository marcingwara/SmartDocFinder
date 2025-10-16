from app.vertex_utils import summarize_text
from app.pdf_utils import extract_text_from_pdf
import logging
import re
from collections import Counter
from langdetect import detect

logger = logging.getLogger(__name__)

def detect_language_safe(text: str) -> str:
    """Bezpieczne wykrywanie języka (fallback na 'pl')."""
    try:
        lang = detect(text)
        return lang if lang else "pl"
    except Exception:
        return "pl"

def analyze_pdf(path_or_bytes) -> str:
    """
    Generate a meaningful summary for the document using Vertex AI if available,
    otherwise keyword-based local summary. Automatically matches document language.
    """
    try:
        # 1️⃣ Extract text
        if isinstance(path_or_bytes, (bytes, bytearray)):
            text = path_or_bytes.decode('utf-8', errors='ignore')
        else:
            text = extract_text_from_pdf(path_or_bytes)

        if not text or len(text.strip()) == 0:
            return "Brak treści w pliku PDF."

        text = text.replace("\n", " ").strip()
        text = re.sub(r"\s+", " ", text)
        text = text[:15000]

        # 2️⃣ Detect language
        lang = detect_language_safe(text)
        logger.info(f"[AI] Detected language: {lang}")

        # 3️⃣ Try Vertex AI summary (prompt zależny od języka)
        prompt_prefix = {
            "pl": "Streść poniższy tekst w kilku zdaniach w języku polskim:",
            "en": "Summarize the following text in English in a few sentences:",
            "de": "Fasse den folgenden Text auf Deutsch in wenigen Sätzen zusammen:",
        }.get(lang, "Summarize the following text briefly:")

        summary = summarize_text(f"{prompt_prefix}\n\n{text}")

        if summary and summary.strip():
            return summary.strip()

        # 4️⃣ Local fallback (keyword-based)
        words = re.findall(r"\b\w{5,}\b", text.lower())  # słowa dłuższe niż 4 znaki
        common = [w for w, _ in Counter(words).most_common(10)]
        keywords = ", ".join(common[:7])

        sentences = re.split(r'(?<=[.!?])\s+', text)
        middle_section = sentences[len(sentences)//3 : len(sentences)//3 + 3]
        preview = " ".join(middle_section)

        # Dopasowanie języka w lokalnym streszczeniu
        if lang == "pl":
            summary_text = (
                f"Dokument dotyczy tematów takich jak: {keywords}. "
                f"Opisuje kluczowe zagadnienia, m.in. {common[0] if common else 'temat główny'}. "
                f"Omawia również: {preview[:400].strip()}..."
            )
        elif lang == "en":
            summary_text = (
                f"The document covers topics such as: {keywords}. "
                f"It describes key issues like {common[0] if common else 'the main topic'}. "
                f"It also discusses: {preview[:400].strip()}..."
            )
        else:
            summary_text = (
                f"Main topics: {keywords}. "
                f"Key point: {common[0] if common else 'main subject'}. "
                f"Excerpt: {preview[:400].strip()}..."
            )

        return summary_text

    except Exception as e:
        logger.error(f"[AI] Error analyzing PDF: {e}")
        return "Błąd generowania streszczenia."

# --- Detect document language ---
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0  # stabilny wynik

def detect_language(text: str) -> str:
    """Detect the dominant language of a text fragment."""
    try:
        if not text or len(text.strip()) < 20:
            return "unknown"
        return detect(text)
    except Exception:
        return "unknown"