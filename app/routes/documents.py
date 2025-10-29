# --- Standard library imports ---
import shutil
import logging
import unicodedata
import urllib.parse
from pathlib import Path
import os
from urllib.parse import unquote

# --- Third-party libraries ---
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import FileResponse, JSONResponse
import vertexai
from vertexai.generative_models import GenerativeModel

# --- Internal project imports ---
from app import db
from app.pdf_utils import extract_text_from_pdf
from app.ai_utils import analyze_pdf, detect_language, ask_ai, suggest_dynamic_folders
from app.ai_chat import answer_question
from app.vertex_utils import get_vertex_status
from app.elasticsearch_utils import (
    index_pdf,
    search as es_search,
    delete_from_index,
    clear_index,
    create_index,
    check_connection,
    es,
    ES_INDEX,
)

print("✅ LOADED DOCUMENTS ROUTER from:", __file__)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Documents"])

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_FOLDER = BASE_DIR / "uploaded_pdfs"
UPLOAD_FOLDER.mkdir(exist_ok=True)

def _safe_filename(name: str) -> str:
    # Normalize and strip path
    name = Path(name).name
    name = unicodedata.normalize("NFKD", name)
    return name

def _content_disposition_filename_header(filename: str, disposition: str = "inline"):
    """
    Provide RFC5987 compatible filename* header for unicode.
    We'll return a dict for headers to set on FileResponse.
    """
    try:
        ascii_name = filename.encode("latin-1")
        header = f'{disposition}; filename="{filename}"'
        return {"Content-Disposition": header}
    except Exception:
        # Use filename* UTF-8 fallback
        quoted = urllib.parse.quote(filename)
        header = f"{disposition}; filename*=UTF-8''{quoted}"
        return {"Content-Disposition": header}



# Upload single
@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    filename = _safe_filename(file.filename)
    dest = UPLOAD_FOLDER / filename

    # 🔍 Check if file already exists
    existing = db.get_document(filename)
    if existing or dest.exists():
        existing_path = dest if dest.exists() else Path(existing["filepath"])
        folder_rel = existing_path.parent.relative_to(Path.cwd())
        return JSONResponse(
            status_code=409,
            content={
                "detail": "File already exists",
                "filename": filename,
                "folder": str(folder_rel),
            },
        )

    # 📥 Save file if new
    data = await file.read()
    dest.write_bytes(data)
    db.add_document(filename, dest)

    preview = extract_text_from_pdf(dest)[:1000]
    summary = analyze_pdf(dest)

    # Language detection

    lang_sample = extract_text_from_pdf(dest)[:2000]
    language = detect_language(lang_sample)

    index_pdf(dest, filename, summary, language)

    return {
        "filename": filename,
        "preview": preview,
        "summary": summary,
        "language": language,
    }


# Upload multiple
@router.post("/upload-multiple")
async def upload_multiple(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append({"filename": file.filename, "status": "skipped - not pdf"})
            continue

        filename = _safe_filename(file.filename)
        dest = UPLOAD_FOLDER / filename

        # 🔍 Duplicate check
        existing = db.get_document(filename)
        if existing or dest.exists():
            existing_path = dest if dest.exists() else Path(existing["filepath"])
            folder_rel = existing_path.parent.relative_to(Path.cwd())
            results.append({
                "filename": filename,
                "status": "duplicate",
                "folder": str(folder_rel),
            })
            continue

        # 📥 Save new file
        data = await file.read()
        dest.write_bytes(data)
        db.add_document(filename, dest)

        preview = extract_text_from_pdf(dest)[:500]
        summary = analyze_pdf(dest)
        index_pdf(dest, filename, summary)

        results.append({
            "filename": filename,
            "status": "uploaded",
            "preview": preview,
            "summary": summary,
        })

    return {"uploaded": results}
# List
@router.get("/")
async def list_documents():
    """
    Zwraca listę dokumentów tylko z katalogu głównego (bez tych przeniesionych do folderów).
    """
    docs = db.list_documents()
    out = []

    for d in docs:
        filepath = Path(d["filepath"])

        # 🔹 pomiń pliki, które znajdują się w folderach
        if "folders" in filepath.parts:
            continue

        try:
            preview = extract_text_from_pdf(filepath)[:300]
            summary = analyze_pdf(filepath)
            lang_sample = extract_text_from_pdf(filepath)[:2000]
            language = detect_language(lang_sample)
        except Exception:
            preview = ""
            summary = ""
            language = "unknown"

        out.append({
            "filename": d["filename"],
            "preview": preview,
            "summary": summary,
            "language": language
        })

    return out

# View
@router.get("/view/{filename}")
async def view_pdf(filename: str):
    rec = db.get_document(filename)
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(rec["filepath"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    headers = _content_disposition_filename_header(filename, disposition="inline")
    return FileResponse(path, media_type="application/pdf", headers=headers)

# Download
@router.get("/download/{filename}")
async def download_pdf(filename: str):
    rec = db.get_document(filename)
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(rec["filepath"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    headers = _content_disposition_filename_header(filename, disposition="attachment")
    return FileResponse(path, media_type="application/pdf", headers=headers)

# Delete
@router.delete("/file/{filename:path}")
async def delete_document(filename: str):
    import os
    print("🚀 delete_document CALLED - TEST BUILD 1")
    """
    Deletes a PDF file from uploaded_pdfs/ or uploaded_pdfs/folders/.
    Works even if DB record is missing.
    """

    try:
        # 🔹 Decode special characters
        safe_name = unquote(filename)
        print(f"🗑️ Request to delete: {safe_name}")

        # 🔹 Look up DB first
        rec = db.get_document(safe_name)
        if rec and "filepath" in rec:
            path = Path(rec["filepath"])
        else:
            # Try finding on disk
            path = None
            candidates = [
                UPLOAD_FOLDER / safe_name,
                UPLOAD_FOLDER / "folders" / safe_name,
                ]
            for c in candidates:
                if c.exists():
                    path = c
                    break
            if not path:
                # recursive search
                for root, _, files in os.walk(UPLOAD_FOLDER):
                    if Path(safe_name).name in files:
                        path = Path(root) / Path(safe_name).name
                        break

        if not path or not path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")

        # 🧹 Delete file
        path.unlink()
        print(f"✅ Deleted: {path}")

        # 🔄 Clean up index + DB
        try:
            db.delete_document(safe_name)
            delete_from_index(safe_name)
        except Exception as cleanup_err:
            print(f"⚠️ Cleanup warning: {cleanup_err}")

        return {"deleted": safe_name}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

# Search
@router.get("/search")
async def search_documents(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    results = es_search(query)
    output = []

    for r in results:
        try:
            # Pobierz dane ze źródła (Elasticsearch zwraca często pod "_source")
            source = r.get("_source", r)

            filepath = Path(source.get("path", ""))
            preview = extract_text_from_pdf(filepath)[:300] if filepath.exists() else ""
            summary = source.get("summary", "") or (analyze_pdf(filepath) if filepath.exists() else "")
            language = source.get("language", "unknown")

            # Jeśli language nie ma, spróbuj z metadanych pliku
            if language == "unknown" and filepath.exists():

                text_sample = extract_text_from_pdf(filepath)[:2000]
                language = detect_language(text_sample) or "unknown"

            output.append({
                "filename": source.get("filename", "unknown"),
                "preview": preview,
                "summary": summary,
                "language": language
            })

        except Exception as e:
            print(f"[SEARCH ERROR] {e}")
            output.append({
                "filename": r.get("filename", "unknown"),
                "preview": "",
                "summary": "",
                "language": "unknown"
            })

    return output
# Clear index
@router.delete("/clear-index")
async def clear_elasticsearch_index():
    clear_index()
    return {"message": "✅ Elasticsearch index cleared successfully."}

# Reindex all
@router.post("/reindex-all")
async def reindex_all():
    create_index()
    docs = db.list_documents()
    count = 0
    for d in docs:
        p = Path(d["filepath"])
        if p.exists():
            index_pdf(p, d["filename"])
            count += 1
    return {"message": f"✅ Reindexed {count} documents in Elasticsearch."}

# =============================
# 🧠 ADMIN HEALTH ENDPOINT (pełny + stabilny)
# =============================
@router.get("/admin/health")
async def admin_health():
    """Zwraca stan aplikacji, Elasticsearch i Vertex AI (z automatycznym wykrywaniem modelu)."""

    # 🔹 Elasticsearch
    es_ok = check_connection()

    # 🔹 Vertex AI – szybki status z vertex_utils
    vertex_info = get_vertex_status()

    # 🔹 Próba dynamicznego wykrycia modelu (tylko jeśli Vertex jest włączony)
    vertex_model = vertex_info.get("model", "—")
    if vertex_info.get("enabled"):
        try:

            # próba inicjalizacji (nie blokuje, jeśli już zainicjalizowany)
            vertexai.init(project=vertex_info.get("project"), location=vertex_info.get("region"))

            # próbujemy sprawdzić realny model – jeśli się uda, nadpisz
            model = GenerativeModel.from_pretrained("gemini-1.5-pro")
            vertex_model = getattr(model, "name", None) or "gemini-1.5-pro"

        except Exception as inner_e:
            print(f"[VertexAI] Model detection failed: {inner_e}")
            # nie blokujemy – zostawiamy dane z vertex_utils

    # 🔹 Zbuduj pełną odpowiedź
    return {
        "app": "running",
        "elasticsearch": {
            "connected": es_ok,
            "index": "pdf_documents" if es_ok else None,
            "docs": "OK" if es_ok else "unavailable",
        },
        "vertex_ai": {
            "enabled": vertex_info.get("enabled", False),
            "model": vertex_model,
        },
    }

# =============================
# 📁 FOLDERS MANAGEMENT ENDPOINTS
# =============================


FOLDERS_ROOT = UPLOAD_FOLDER / "folders"
FOLDERS_ROOT.mkdir(exist_ok=True)


@router.get("/folders")
async def list_folders():
    """Zwraca listę wszystkich folderów w katalogu upload."""
    folders = [f.name for f in FOLDERS_ROOT.iterdir() if f.is_dir()]
    return {"folders": folders}


@router.post("/folders")
async def create_folder(data: dict = Body(...)):
    """Tworzy nowy folder w katalogu upload."""
    folder_name = data.get("name", "").strip()
    if not folder_name:
        raise HTTPException(status_code=400, detail="Folder name required")

    new_folder = FOLDERS_ROOT / folder_name
    if new_folder.exists():
        raise HTTPException(status_code=400, detail="Folder already exists")

    new_folder.mkdir(parents=True, exist_ok=False)
    return {"message": f"✅ Folder '{folder_name}' created successfully."}

@router.delete("/folders/{name}")
async def delete_folder(name: str):

    """
    Usuwa pusty folder z katalogu upload/folders.
    Jeśli folder nie istnieje lub zawiera pliki — zgłasza błąd.
    """
    folder_path = FOLDERS_ROOT / name

    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")

    # Sprawdź, czy folder jest pusty
    if any(folder_path.iterdir()):
        raise HTTPException(status_code=400, detail="Folder is not empty. Remove files first.")

    try:
        folder_path.rmdir()
        return {"message": f"✅ Folder '{name}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete folder: {e}")

@router.post("/folders/move")
async def move_file_to_folder(data: dict = Body(...)):
    filename = data.get("filename")
    folder = data.get("folder")

    if not filename or not folder:
        raise HTTPException(status_code=400, detail="Both filename and folder required")

    src = UPLOAD_FOLDER / filename
    dest_folder = FOLDERS_ROOT / folder
    dest = dest_folder / filename

    # szukaj także w podfolderach
    if not src.exists():
        for subfolder in FOLDERS_ROOT.iterdir():
            candidate = subfolder / filename
            if candidate.exists():
                src = candidate
                break

    if not src.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    if not dest_folder.exists():
        raise HTTPException(status_code=404, detail=f"Destination folder '{folder}' not found")


    shutil.move(str(src), str(dest))

    # 🔴 BEZ TEGO view/download/delete po przeniesieniu będą się wywalać

    db.add_document(filename, dest)  # <— aktualizacja ścieżki w SQLite

    # (opcjonalnie) zaktualizuj ścieżkę w Elasticsearch, jeśli używasz:
    try:

        es.update_by_query(
            index=ES_INDEX,
            body={
                "script": {"source": "ctx._source.path = params.p", "params": {"p": str(dest)}},
                "query": {"term": {"filename": {"value": filename}}},
            },
            refresh=True,
        )
    except Exception as e:
        print(f"[ES WARN] Path update failed for {filename}: {e}")

    return {"message": f"✅ File '{filename}' moved to folder '{folder}'"}

@router.get("/folders/{name}")
async def list_folder_contents(name: str):
    """Zwraca listę plików w wybranym folderze."""
    folder_path = FOLDERS_ROOT / name
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")

    files = [f.name for f in folder_path.iterdir() if f.is_file()]
    return {"folder": name, "files": files}

# =============================
# 📦 MOVE FILE TO FOLDER + UPDATE ES
# =============================
@router.post("/move-to-folder")
async def move_to_folder(data: dict = Body(...)):
    """
    Przenosi plik z głównego katalogu do wskazanego folderu.
    Zachowuje wpis w Elasticsearch (aktualizuje ścieżkę).
    Body: { "filename": "plik.pdf", "folder": "raporty" }
    """
    filename = data.get("filename")
    folder_name = data.get("folder")

    if not filename or not folder_name:
        raise HTTPException(status_code=400, detail="Missing filename or folder")

    src = UPLOAD_FOLDER / filename
    dest_folder = FOLDERS_ROOT / folder_name
    dest = dest_folder / filename

    if not src.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not dest_folder.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    # Przenieś fizycznie plik
    src.rename(dest)

    # 🔹 aktualizuj ścieżkę w SQLite

    db.add_document(filename, dest)

    # 🔹 aktualizuj Elasticsearch (aktualizujemy tylko path)

    try:
        es.update_by_query(
            index=ES_INDEX,
            body={
                "script": {
                    "source": "ctx._source.path = params.new_path",
                    "params": {"new_path": str(dest)},
                },
                "query": {"term": {"filename": {"value": filename}}},
            },
            refresh=True
        )
        print(f"[ES] Path updated for {filename}")
    except Exception as e:
        print(f"[ES WARN] Could not update path for {filename}: {e}")

    return {"message": f"✅ File '{filename}' moved to folder '{folder_name}'."}

# =============================
# 🤖 AI Dynamic Folder Organization
# =============================
@router.get("/ai/suggest-dynamic-folders")
async def ai_suggest_dynamic_folders():
    """
    Analyze indexed documents and suggest smart folder groupings using Vertex AI.
    """


    if not check_connection():
        return {"error": "Elasticsearch not available"}

    # Pobierz wszystkie dokumenty z Elasticsearch
    try:
        docs = es.search(index=ES_INDEX, body={"query": {"match_all": {}}, "size": 50})
        hits = docs.get("hits", {}).get("hits", [])
        if not hits:
            return {"folders": [], "message": "No indexed documents found."}

        docs_data = [
            {
                "filename": h["_source"].get("filename", ""),
                "summary": h["_source"].get("summary", ""),
                "language": h["_source"].get("language", "unknown"),
            }
            for h in hits
        ]

        # AI grupuje dokumenty
        suggestions = suggest_dynamic_folders(docs_data)
        return {"folders": suggestions}

    except Exception as e:
        print(f"[AI Dynamic Folder Error] {e}")
        return {"error": str(e), "folders": []}

# --- Q&A over documents ---

@router.post("/qa")
async def qa_endpoint(payload: dict = Body(...)):
    """
    Body: { "question": "..." }
    Zwraca: { "answer": "...", "sources": ["file1.pdf", ...] }
    """
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    result = answer_question(question)
    return result

# =============================
# 💬 ASK AI ENDPOINT
# =============================
@router.get("/ai/query")
async def ai_query(text: str):
    """
    Umożliwia użytkownikowi zadanie pytania AI.
    Automatycznie wykrywa język i zwraca odpowiedź w tym języku.
    """


    if not text or len(text.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    answer = ask_ai(text)
    return {"query": text, "answer": answer}

# ============================================
# 🧹 ADMIN CLEANUP ENDPOINT (v2 – z logami)
# ============================================


@router.delete("/admin/cleanup", tags=["Admin"])
def cleanup_missing_files():
    """
    Usuwa z bazy i Elasticsearch pliki, które nie istnieją fizycznie.
    """
    base_dir = "uploaded_pdfs"
    removed = []
    failed = []

    try:
        all_docs = db.get_all_documents()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"❌ DB read failed: {str(e)}"}
        )

    for doc in all_docs:
        filename = doc.get("filename")
        if not filename:
            continue

        file_path = os.path.join(base_dir, filename)

        if not os.path.exists(file_path):
            try:
                db.delete_document(filename)
                delete_from_index(filename)
                removed.append(filename)
                print(f"[CLEANUP] Removed: {filename}")
            except Exception as e:
                print(f"[CLEANUP] ❌ Failed to remove {filename}: {e}")
                failed.append({"file": filename, "error": str(e)})

    return {
        "message": f"🧹 Cleanup finished. Removed {len(removed)} missing files.",
        "removed": removed,
        "failed": failed
    }