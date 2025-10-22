import vertexai
from vertexai.language_models import TextEmbeddingModel

# === Vertex AI initialization ===
PROJECT_ID = "smartdocfinder-ai"
REGION = "us-central1"

vertexai.init(project=PROJECT_ID, location=REGION)
print(f"[VertexAI] Initialized for project '{PROJECT_ID}' in region '{REGION}'")

def generate_text_embeddings(text: str):
    """Generate text embeddings using Vertex AI (text-embedding-004)."""
    try:
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        embeddings = model.get_embeddings([text])
        vector = embeddings[0].values
        print(f"[INFO] Generated embedding of length {len(vector)}")
        return vector
    except Exception as e:
        print(f"[ERROR] Vertex AI embedding failed: {e}")
        return []