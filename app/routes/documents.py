from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import unicodedata
import urllib.parse
from app.pdf_utils import extract_text_from_pdf
from app.ai_utils import analyze_pdf, detect_language
from app import db
from app.elasticsearch_utils import index_pdf, search as es_search, delete_from_index, clear_index, create_index
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

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
    data = await file.read()
    dest = UPLOAD_FOLDER / filename

    if dest.exists():
        filename = f"{Path(filename).stem}_{uuid.uuid4().hex[:6]}{Path(filename).suffix}"
        dest = UPLOAD_FOLDER / filename

    dest.write_bytes(data)
    db.add_document(filename, dest)

    preview = extract_text_from_pdf(dest)[:1000]
    summary = analyze_pdf(dest)

# Extract short text for language detection
    lang_sample = extract_text_from_pdf(dest)[:2000]
    language = detect_language(lang_sample)
    index_pdf(dest, filename, summary)

    return {"filename": filename, "preview": preview, "summary": summary, "language": language}
# Upload multiple
@router.post("/upload-multiple")
async def upload_multiple(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append({"filename": file.filename, "status": "skipped - not pdf"})
            continue
        filename = _safe_filename(file.filename)
        data = await file.read()
        dest = UPLOAD_FOLDER / filename
        if dest.exists():
            filename = f"{Path(filename).stem}_{uuid.uuid4().hex[:6]}{Path(filename).suffix}"
            dest = UPLOAD_FOLDER / filename
        dest.write_bytes(data)
        db.add_document(filename, dest)
        preview = extract_text_from_pdf(dest)[:500]
        summary = analyze_pdf(dest)
        index_pdf(dest, filename, summary)
        results.append({"filename": filename, "preview": preview, "summary": summary})
    return {"uploaded": results}

# List
@router.get("/")
async def list_documents():
    docs = db.list_documents()
    out = []
    for d in docs:
        try:
            filepath = Path(d["filepath"])
            preview = extract_text_from_pdf(filepath)[:300]
            summary = analyze_pdf(filepath)
        except Exception:
            preview = ""
            summary = ""
        out.append({"filename": d["filename"], "preview": preview, "summary": summary})
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
@router.delete("/file/{filename}")
async def delete_document(filename: str):
    rec = db.get_document(filename)
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(rec["filepath"])
    if path.exists():
        path.unlink()
    db.delete_document(filename)
    delete_from_index(filename)
    return {"deleted": filename}

# Search
@router.get("/search")
async def search_documents(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    results = es_search(query)
    output = []
    for r in results:
        try:
            filepath = Path(r.get("path", ""))
            preview = extract_text_from_pdf(filepath)[:300] if filepath.exists() else ""
            summary = r.get("summary", "") or (analyze_pdf(filepath) if filepath.exists() else "")
            output.append({
                "filename": r.get("filename", "unknown"),
                "preview": preview,
                "summary": summary,
                "language": r.get("language", "unknown")
            })
        except Exception:
            output.append({"filename": r.get("filename", "unknown"), "preview": "", "summary": ""})
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