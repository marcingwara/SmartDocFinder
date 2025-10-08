from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app import db
from app.pdf_utils import extract_text_from_pdf
from pathlib import Path
from typing import List

router = APIRouter()
UPLOAD_FOLDER = Path("uploaded_pdfs")
UPLOAD_FOLDER.mkdir(exist_ok=True)

# initialize DB (create or migrate)
db.init_db()

def _safe_filename(name: str) -> str:
    return Path(name).name

@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    filename = _safe_filename(file.filename)
    data = await file.read()  # read bytes once
    dest = UPLOAD_FOLDER / filename

    # handle name conflicts by adding numeric suffix
    counter = 1
    base = dest.stem
    suffix = dest.suffix
    while dest.exists():
        dest = UPLOAD_FOLDER / f"{base}_{counter}{suffix}"
        counter += 1

    dest.write_bytes(data)
    db.add_document(dest.name, dest)

    preview = extract_text_from_pdf(data)[:1000]
    return {"filename": dest.name, "preview": preview}

@router.post("/upload-multiple-pdfs")
async def upload_multiple_pdfs(files: List[UploadFile] = File(...)):
    uploaded = []
    for file in files:
        filename = _safe_filename(file.filename)
        data = await file.read()
        dest = UPLOAD_FOLDER / filename
        counter = 1
        base = dest.stem
        suffix = dest.suffix
        while dest.exists():
            dest = UPLOAD_FOLDER / f"{base}_{counter}{suffix}"
            counter += 1
        dest.write_bytes(data)
        db.add_document(dest.name, dest)
        uploaded.append({"filename": dest.name})
    return {"uploaded": uploaded}

@router.get("/")
async def list_documents():
    # return a list (frontend expects array)
    return db.get_all_documents()

@router.get("/file/{filename}")
async def get_document_file(filename: str):
    doc = db.get_document_by_filename(filename)
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(doc["filepath"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(path)

@router.get("/search")
async def search_documents(query: str):
    if not query:
        return []
    results = []
    for doc in db.get_all_documents():
        text = extract_text_from_pdf(Path(doc["filepath"]))
        idx = text.lower().find(query.lower())
        if idx != -1:
            start = max(0, idx - 80)
            end = min(len(text), idx + len(query) + 80)
            snippet = text[start:end].replace("\n", " ")
            results.append({"filename": doc["filename"], "snippet": snippet})
    return results

@router.delete("/delete/{filename}")
async def delete_document(filename: str):
    doc = db.get_document_by_filename(filename)
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(doc["filepath"])
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass
    db.delete_document(filename)
    return {"status": "deleted", "filename": filename}