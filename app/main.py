import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# --- Importy projektu ---
from app.routes.documents import router as documents_router
from app import db

# --- Inicjalizacja ---
load_dotenv()
db.cleanup_missing_files()

app = FastAPI(title="SmartDocFinder API")

# ==========================
# 🔒 CORS — tylko Twoje domeny produkcyjne
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://storage.googleapis.com",
        "https://storage.googleapis.com/smartdocfinder-frontend",
        "https://smartdocfinder-861730700785.europe-west1.run.app",
        "https://smartdocfinder-861730700785-europe-west1.run.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ==========================
# 🌐 Middleware — wymuszenie HTTPS (fix błędu redirect 307)
# ==========================
@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if request.url.scheme == "http":
        # wymusza HTTPS — ważne przy połączeniach z GCS
        https_url = request.url.replace(scheme="https")
        return RedirectResponse(url=str(https_url))
    response = await call_next(request)
    return response

# ==========================
# 📁 Ścieżki statyczne (frontend, bannery)
# ==========================
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
BANNERS_DIR = FRONTEND_DIR / "banners"

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

if BANNERS_DIR.exists():
    app.mount("/banners", StaticFiles(directory=str(BANNERS_DIR)), name="banners")

# ==========================
# 🚀 Główne endpointy API
# ==========================
app.include_router(documents_router, prefix="/documents")

# ==========================
# 🧭 Endpoint kontrolny
# ==========================
@app.get("/")
async def root():
    """Prosty test, by sprawdzić czy backend działa."""
    return {
        "message": "🚀 SmartDocFinder API is running on Cloud Run",
        "frontend": "https://storage.googleapis.com/smartdocfinder-frontend/index.html",
        "status": "ok"
    }