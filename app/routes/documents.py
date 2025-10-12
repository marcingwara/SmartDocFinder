from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import unicodedata

from app.pdf_utils import extract_text_from_pdf
from app.ai_utils import analyze_pdf
from app import db
from app.elasticsearch_utils import index_pdf, search as es_search, delete_from_index, clear_index

router = APIRouter(prefix="/documents", tags=["Documents"])

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_FOLDER = BASE_DIR / "uploaded_pdfs"
UPLOAD_FOLDER.mkdir(exist_ok=True)


def _safe_filename(name: str) -> str:
    """Normalize and sanitize filenames to avoid encoding issues."""
    return Path(unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")).name


# --- Upload single PDF
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
    index_pdf(dest, filename, summary)

    return {"filename": filename, "preview": preview, "summary": summary}


# --- Upload multiple PDFs
@router.post("/upload-multiple")
async def upload_multiple(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append({"filename": file.filename, "status": "❌ Skipped (not a PDF)"})
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

        results.append({
            "filename": filename,
            "preview": preview,
            "summary": summary
        })
    return {"uploaded": results}


# --- List all documents
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
        out.append({
            "filename": d["filename"],
            "preview": preview,
            "summary": summary
        })
    return out


# --- View PDF in browser (inline)
@router.get("/view/{filename}")
async def view_pdf(filename: str):
    rec = db.get_document(filename)
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")

    path = Path(rec["filepath"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    safe_filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")

    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'}
    )


# --- Download PDF
@router.get("/download/{filename}")
async def download_pdf(filename: str):
    rec = db.get_document(filename)
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")

    path = Path(rec["filepath"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    safe_filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")

    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )


# --- Delete PDF
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

    safe_filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")

    return {"deleted": safe_filename, "message": "✅ File deleted successfully."}


# --- Search PDFs (Elasticsearch)
@router.get("/search")
async def search_documents(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    try:
        results = es_search(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    output = []
    for r in results:
        filename = r.get("filename", "unknown")
        path = Path(r.get("path", ""))
        author = r.get("author", "Unknown")
        pages = r.get("number_of_pages", 0)
        created = r.get("created_date", "")
        summary = r.get("summary", "")

        preview = ""
        if path.exists():
            try:
                preview = extract_text_from_pdf(path)[:300]
            except Exception:
                preview = ""

        output.append({
            "filename": filename,
            "author": author,
            "pages": pages,
            "created_date": created,
            "summary": summary,
            "preview": preview
        })

    return output


# --- Clear Elasticsearch index
@router.delete("/clear-index")
async def clear_elasticsearch_index():
    clear_index()
    return {"message": "✅ Elasticsearch index cleared successfully."}

@router.post("/reindex-all")
async def reindex_all():
    """
    Reindex all PDFs in the upload folder into Elasticsearch.
    """
    from app.elasticsearch_utils import index_pdf, create_index
    from app import db

    create_index()
    docs = db.list_documents()
    count = 0

    for d in docs:
       path = Path (d["filepath"])
       if path.exists():
           index_pdf(path, d["filename"])
           count += 1

    return {"message": f"✅ Reindexed {count} documents in Elasticsearch."}
