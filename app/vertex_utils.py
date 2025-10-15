import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# If you use service key file inside project, ensure env var set:
DEFAULT_KEY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vertex_key.json")
if os.path.exists(DEFAULT_KEY) and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = DEFAULT_KEY

# Use google-cloud-aiplatform (vertexai) when available
try:
    import vertexai
    from vertexai.preview import language_models, TextGenerationModel
    from vertexai.preview._services import embeddings as emb_module  # fallback safe import
    from google.cloud import aiplatform
    VERTEX_AVAILABLE = True
except Exception as e:
    VERTEX_AVAILABLE = False
    logger.warning("Vertex AI not available: %s", e)

def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector via Vertex AI. If unavailable, return empty list.
    """
    if not VERTEX_AVAILABLE:
        logger.warning("Vertex not available - embedding skipped.")
        return []

    try:
        # new Vertex generative APIs may vary by version — attempt to use text embedding model
        # This code uses the `vertexai` preview APIs when available
        from vertexai.preview._model_garden import TextEmbeddingModel as _T
        # Try to instantiate known model names; this may require adjustment to model name in your project
        model = _T.from_pretrained("textembedding-gecko@003")
        emb = model.predict(text)
        return list(emb.values) if hasattr(emb, "values") else list(emb.embedding)
    except Exception as e:
        logger.error("[VertexAI] Embedding failed: %s", e)
        return []

def summarize_text(text: str, max_length: int = 300) -> str:
    """
    Generate a short summary using Vertex / fallback. Keep it small.
    """
    if not VERTEX_AVAILABLE:
        return ""

    try:
        # Try language model generation approach; API has changed across versions
        # Using vertexai.preview.language_models.TextGenerationModel as generic generator
        model = TextGenerationModel.from_pretrained("text-bison@001")
        prompt = f"Summarize the following text into one short paragraph (max {max_length} characters):\n\n{text}"
        resp = model.predict(prompt, temperature=0.0, max_output_tokens=200)
        return resp.text.strip() if resp and hasattr(resp, "text") else str(resp)
    except Exception as e:
        logger.error("[VertexAI] Summary failed: %s", e)
        return ""