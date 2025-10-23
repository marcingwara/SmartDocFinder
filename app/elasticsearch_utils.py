import os
from datetime import datetime
from elasticsearch import Elasticsearch, exceptions, helpers
from app.pdf_utils import extract_text_from_pdf
from PyPDF2 import PdfReader

# --- Konfiguracja środowiska ---
ELASTIC_URL = os.getenv("ELASTIC_URL")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")
ES_INDEX = os.getenv("ELASTIC_INDEX", "search-wky3")

# --- Inicjalizacja klienta ---
es = None
if ELASTIC_URL and ELASTIC_API_KEY:
    try:
        es = Elasticsearch(
            ELASTIC_URL,
            api_key=ELASTIC_API_KEY,
            verify_certs=False,           # ⚠️ wyłączone, bo Elastic Cloud ma certyfikaty GCP
            ssl_show_warn=False,
            request_timeout=60,
            retry_on_timeout=True,
        )
        print(f"[ES] ✅ Connecting to Elastic Cloud: {ELASTIC_URL}")
        print("[ES] 🔄 Ping:", es.ping())
    except Exception as e:
        print(f"[ES] ❌ Failed to connect: {e}")
else:
    print("[ES] ⚠️ Missing ELASTIC_URL or ELASTIC_API_KEY. Running in local/offline mode.")


# --- Pomocnicze funkcje ---
def check_connection():
    """Sprawdź połączenie z Elastic Cloud."""
    if not es:
        return False
    try:
        ping = es.ping()
        print(f"[ES] 🔄 Ping status: {ping}")
        return ping
    except Exception as e:
        print(f"[ES] ⚠️ Ping error: {e}")
        return False


def create_index():
    """Utwórz index jeśli nie istnieje."""
    if not es or not check_connection():
        print("[ES] ⚠️ Elasticsearch not available – skipping index creation.")
        return

    try:
        if not es.indices.exists(index=ES_INDEX):
            es.indices.create(index=ES_INDEX, body={
                "settings": {
                    "index": {"number_of_shards": 1},
                    "analysis": {"analyzer": {"default": {"type": "standard"}}}
                },
                "mappings": {
                    "properties": {
                        "filename": {"type": "keyword"},
                        "path": {"type": "keyword"},
                        "author": {"type": "text"},
                        "number_of_pages": {"type": "integer"},
                        "created_date": {"type": "date"},
                        "summary": {"type": "text"},
                        "content": {"type": "text"},
                        "language": {"type": "keyword"},
                        "upload_date": {"type": "date"}
                    }
                }
            })
            print(f"[ES] ✅ Created index: {ES_INDEX}")
        else:
            print(f"[ES] ℹ️ Index already exists: {ES_INDEX}")
    except Exception as e:
        print(f"[ES] ⚠️ Failed to create index: {e}")


def extract_metadata(path: str):
    """Pobierz dane z pliku PDF."""
    try:
        reader = PdfReader(path)
        info = reader.metadata or {}
        author = info.get("/Author", "Unknown")
        created = info.get("/CreationDate", "")
        if created.startswith("D:"):
            created = datetime.strptime(created[2:16], "%Y%m%d%H%M%S")
        else:
            created = None
        return {
            "author": author,
            "number_of_pages": len(reader.pages),
            "created_date": created
        }
    except Exception as e:
        print(f"[ES] ⚠️ Metadata extraction failed for {path}: {e}")
        return {"author": "Unknown", "number_of_pages": 0, "created_date": None}


def index_pdf(path, filename, summary="", language="unknown"):
    """Indeksuj dokument PDF."""
    if not es or not check_connection():
        print("[ES] ⚠️ Elasticsearch not available – skipping indexing.")
        return

    create_index()

    try:
        text = extract_text_from_pdf(path)
        if not text.strip():
            text = "(empty document)"

        metadata = extract_metadata(path)
        doc = {
            "filename": filename,
            "path": str(path),
            "content": text,
            "summary": summary or "",
            "author": metadata["author"],
            "number_of_pages": metadata["number_of_pages"],
            "created_date": metadata["created_date"],
            "language": language,
            "upload_date": datetime.utcnow().isoformat()
        }

        es.index(index=ES_INDEX, document=doc, id=filename)
        print(f"[ES] ✅ Indexed {filename}")
    except Exception as e:
        print(f"[ES] ❌ Failed to index {filename}: {e}")


def search(query: str):
    """Wyszukiwanie pełnotekstowe."""
    if not es or not check_connection():
        print("[ES] ⚠️ Elasticsearch unavailable – returning empty result.")
        return []

    try:
        res = es.search(index=ES_INDEX, body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["filename^3", "author^2", "summary", "content"]
                }
            }
        })
        hits = res.get("hits", {}).get("hits", [])
        print(f"[ES] 🔍 Found {len(hits)} results for query: {query}")
        return [h["_source"] for h in hits]
    except Exception as e:
        print(f"[ES] ❌ Search error: {e}")
        return []


def delete_from_index(filename: str):
    """Usuń plik z indeksu."""
    if not es or not check_connection():
        return
    try:
        es.delete_by_query(index=ES_INDEX, body={
            "query": {"term": {"filename": {"value": filename}}}
        })
        print(f"[ES] 🗑️ Deleted {filename}")
    except Exception as e:
        print(f"[ES] ⚠️ Failed to delete {filename}: {e}")


def clear_index():
    """Wyczyść cały indeks."""
    if not es or not check_connection():
        print("[ES] ⚠️ Elasticsearch not connected – cannot clear index.")
        return
    try:
        es.delete_by_query(index=ES_INDEX, body={"query": {"match_all": {}}})
        print("[ES] 🧹 Index cleared.")
    except Exception as e:
        print(f"[ES] ❌ Failed to clear index: {e}")