from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
from app.pdf_utils import extract_text_from_pdf
from app import models
from typing import List

router = APIRouter()

# ensure DB initialized
models.init_db()

UPLOAD_FOLDER = Path("uploaded_pdfs")
UPLOAD_FOLDER.mkdir(exist_ok=True)

@router.post("/upload", status_code=201)
async def upload_pdf(file: UploadFile = File(...)):
    # validate extension
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # read full bytes once
    file_bytes = await file.read()

    # save to disk
    dest = UPLOAD_FOLDER / file.filename
    # if duplicate filename, add suffix
    if dest.exists():
        base = dest.stem
        suffix = dest.suffix
        i = 1
        while True:
            candidate = UPLOAD_FOLDER / f"{base}_{i}{suffix}"
            if not candidate.exists():
                dest = candidate
                break
            i += 1

    with open(dest, "wb") as f:
        f.write(file_bytes)

    # extract text from bytes
    text = extract_text_from_pdf(file_bytes)

    # save metadata/content to DB
    models.add_document(dest.name, str(dest.resolve()), text)

    return {"filename": dest.name, "preview": text[:500]}


@router.post("/upload-multiple", status_code=201)
async def upload_multiple(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            # skip non-pdf files
            continue
        file_bytes = await file.read()
        dest = UPLOAD_FOLDER / file.filename
        if dest.exists():
            base = dest.stem
            suffix = dest.suffix
            i = 1
            while True:
                candidate = UPLOAD_FOLDER / f"{base}_{i}{suffix}"
                if not candidate.exists():
                    dest = candidate
                    break
                i += 1
        with open(dest, "wb") as f:
            f.write(file_bytes)
        text = extract_text_from_pdf(file_bytes)
        models.add_document(dest.name, str(dest.resolve()), text)
        results.append({"filename": dest.name, "preview": text[:500]})
    return {"uploaded": results}


@router.get("/", summary="List uploaded documents")
async def list_documents():
    return {"documents": models.list_documents()}


@router.get("/file/{filename}", summary="Get full text by filename")
async def get_document(filename: str):
    doc = models.get_document_by_filename(filename)
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    return {"filename": doc["filename"], "content": doc["content"]}


@router.get("/search", summary="Search documents' content")
async def search_documents(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter required")
    results = models.search_documents(query)
    # normalized snippet: if snippet is None / empty, provide preview
    out = []
    for r in results:
        snippet = r.get("snippet") or ""
        if not snippet and r.get("found_pos") and r.get("found_pos") > 0:
            snippet = ""
        out.append({
            "filename": r.get("filename"),
            "snippet": snippet[:500]
        })
    return {"results": out}


@router.delete("/{filename}", summary="Delete document by filename")
async def delete_document(filename: str):
    deleted = models.delete_document_by_filename(filename)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    # also remove file from disk if exists
    path = UPLOAD_FOLDER / filename
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass
    return {"deleted": filename}