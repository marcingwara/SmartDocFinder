import os
import logging
from typing import List

logger = logging.getLogger(__name__)

PROJECT_ID = "smartdocfinder-ai"
REGION = "us-central1"

# ✅ Klucz serwisowy (jeśli używasz lokalnie)
DEFAULT_KEY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vertex_key.json")
if os.path.exists(DEFAULT_KEY) and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = DEFAULT_KEY

VERTEX_AVAILABLE = False
ACTIVE_MODEL = "—"

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel

    vertexai.init(project=PROJECT_ID, location=REGION)
    VERTEX_AVAILABLE = True

    # 🔍 spróbuj wykryć, który model faktycznie działa
    try:
        test_model = GenerativeModel("gemini-1.5-pro")
        ACTIVE_MODEL = getattr(test_model, "name", "gemini-1.5-pro")
    except Exception:
        # fallback – jeśli Gemini nie jest dostępny, użyj Bisona
        ACTIVE_MODEL = "text-bison@002"

    print(f"[VertexAI] ✅ Initialized with model: {ACTIVE_MODEL}")

except Exception as e:
    print(f"[VertexAI] ⚠️ Vertex unavailable: {e}")
    VERTEX_AVAILABLE = False
    ACTIVE_MODEL = "—"


def summarize_text(text: str, max_length: int = 300) -> str:
    """Generate a short summary using Vertex AI with robust response handling."""
    if not VERTEX_AVAILABLE:
        return ""
    try:
        from vertexai.generative_models import GenerativeModel
        model = GenerativeModel(ACTIVE_MODEL)
        prompt = f"Summarize this text in one short paragraph (max {max_length} chars):\n\n{text}"
        resp = model.generate_content(prompt)

        # 🔍 DEBUG – zobacz strukturę odpowiedzi
        print("🧠 RAW Vertex response:", repr(resp))

        # ✅ różne wersje odpowiedzi — bezpieczny odczyt
        if hasattr(resp, "text") and resp.text:
            return resp.text.strip()
        elif hasattr(resp, "candidates") and resp.candidates:
            candidate = resp.candidates[0]
            if hasattr(candidate, "content") and candidate.content.parts:
                return candidate.content.parts[0].text.strip()
            elif hasattr(candidate, "text"):
                return candidate.text.strip()
        elif isinstance(resp, str):
            return resp.strip()

        # 🧩 jeśli nic nie działa – konwersja całości do stringa
        return str(resp).strip()

    except Exception as e:
        logger.warning(f"[VertexAI] Summary failed: {e}")
        return ""


def generate_embedding(text: str) -> List[float]:
    """Generate text embedding (non-blocking)."""
    if not VERTEX_AVAILABLE:
        return []
    try:
        from vertexai.language_models import TextEmbeddingModel
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        emb = model.get_embeddings([text])
        return emb[0].values
    except Exception as e:
        logger.warning(f"[VertexAI] Embedding failed: {e}")
        return []


def get_vertex_status():
    """Zwraca podstawowy status Vertex AI (z automatycznym wykrywaniem modelu)."""
    return {
        "enabled": VERTEX_AVAILABLE,
        "model": ACTIVE_MODEL,
    }