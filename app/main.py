import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 📚 Importy aplikacji
from app.routes.documents import router as documents_router
from app import db

# 🧹 Czyszczenie bazy z brakujących plików
db.cleanup_missing_files()

# 🚀 Inicjalizacja aplikacji FastAPI
app = FastAPI(title="SmartDocFinder API")

# ==========================
# 🔒 CORS – tylko produkcyjny dostęp
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://storage.googleapis.com",                           # główny GCS
        "https://storage.googleapis.com/smartdocfinder-frontend",   # Twój hosting GCS
        "https://smartdocfinder-861730700785.europe-west1.run.app", # backend Cloud Run
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# 📁 Ścieżki statyczne (frontend + bannery)
# ==========================
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
BANNERS_DIR = FRONTEND_DIR / "banners"

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

if BANNERS_DIR.exists():
    app.mount("/banners", StaticFiles(directory=str(BANNERS_DIR)), name="banners")

# ==========================
# 🧩 Główne routery API
# ==========================
app.include_router(documents_router, prefix="/documents")

# ==========================
# 🏠 Endpoint główny
# ==========================
@app.get("/")
async def root():
    frontend_url = os.getenv(
        "FRONTEND_URL",
        "https://storage.googleapis.com/smartdocfinder-frontend/index.html"
    )
    return {
        "message": "🚀 SmartDocFinder API is running on Cloud Run",
        "frontend": frontend_url
    }