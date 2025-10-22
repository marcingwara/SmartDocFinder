from elasticsearch import Elasticsearch, exceptions
from app.pdf_utils import extract_text_from_pdf
from PyPDF2 import PdfReader
import os
from datetime import datetime

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ES_INDEX = "pdf_documents"

es = Elasticsearch(ES_HOST)


def check_connection():
    try:
        return es.ping()
    except exceptions.ConnectionError:
        return False


def create_index():
    """Create index if not exists, with language analyzers."""
    if not es.indices.exists(index=ES_INDEX):
        es.indices.create(index=ES_INDEX, body={
            "settings": {
                "analysis": {
                    "analyzer": {
                        "custom_polish": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "polish_stem"]
                        },
                        "custom_english": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "porter_stem"]
                        }
                    },
                    "filter": {
                        "polish_stem": {
                            "type": "stemmer",
                            "language": "light_polish"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "filename": {"type": "keyword"},
                    "path": {"type": "keyword"},
                    "author": {"type": "text"},
                    "number_of_pages": {"type": "integer"},
                    "created_date": {"type": "date"},
                    "summary": {"type": "text", "analyzer": "custom_polish"},
                    "content": {"type": "text", "analyzer": "custom_polish"},
                    "language": {"type": "keyword"},
                    "upload_date": {"type": "date"}
                }
            }
        })
        print("[ES] ✅ Created index with custom analyzer")

def extract_metadata(path: str):
    """Extract author, pages and creation date"""
    try:
        reader = PdfReader(path)
        info = reader.metadata
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
    except Exception:
        return {"author": "Unknown", "number_of_pages": 0, "created_date": None}


def index_pdf(path, filename, summary="",language="unknown"):
    """Index PDF content and metadata in Elasticsearch"""
    if not check_connection():
        print("[WARN] Elasticsearch not available – skipping index.")
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
            "language": str(language),
            "upload_date": datetime.utcnow().isoformat()
        }

        es.index(index=ES_INDEX, document=doc, id=filename)
        print(f"[✅ Indexed] {filename} ({metadata['number_of_pages']} pages)")

    except Exception as e:
        print(f"[ERROR] Failed to index {filename}: {e}")


def search(query: str):
    """Full-text search across all indexed fields (fuzzy + wildcard + match_phrase_prefix)."""
    if not check_connection():
        print("[WARN] Elasticsearch unavailable – returning empty result.")
        return []

    try:
        res = es.search(index=ES_INDEX, body={
            "query": {
                "bool": {
                    "should": [
                        # Dokładne dopasowanie z boostem
                        {"multi_match": {
                            "query": query,
                            "fields": ["filename^3", "author^2", "summary^2", "content"],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }},
                        # Dopasowanie prefiksowe (frazy zaczynające się od zapytania)
                        {"match_phrase_prefix": {
                            "content": {
                                "query": query,
                                "slop": 3
                            }
                        }},
                        # Dopasowanie częściowe (wildcard)
                        {"wildcard": {"content": f"*{query.lower()}*"}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "highlight": {
                "fields": {
                    "content": {},
                    "summary": {}
                }
            }
        })

        hits = res.get("hits", {}).get("hits", [])
        print(f"[ES] Found {len(hits)} results for query: {query}")
        return [h["_source"] for h in hits]

    except Exception as e:
        print(f"[ERROR] Search error: {e}")
        return []


def delete_from_index(filename: str):
    if not check_connection():
        return
    try:
        es.delete_by_query(index=ES_INDEX, body={
            "query": {"term": {"filename": {"value": filename}}}
        })
        print(f"[INFO] Deleted {filename} from Elasticsearch")
    except Exception as e:
        print(f"[WARN] Failed to delete {filename}: {e}")


def clear_index():
    if not check_connection():
        return
    try:
        es.delete_by_query(index=ES_INDEX, body={"query": {"match_all": {}}})
        print("[INFO] Elasticsearch index cleared.")
    except Exception as e:
        print(f"[ERROR] Failed to clear index: {e}")