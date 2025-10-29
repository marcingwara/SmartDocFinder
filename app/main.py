import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Import routera dokumentów
from app.routes.documents import router as documents_router

# Inicjalizacja bazy (jeśli istnieje)
from app import db
db.cleanup_missing_files()

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="SmartDocFinder API")

# ==========================
# 🔒 CORS - dostęp z frontendu
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://storage.googleapis.com",  # ✅ Twój frontend hostowany na GCS
        "https://smartdocfinder-861730700785.europe-west1.run.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# 📁 Ścieżki statyczne (frontend)
# ==========================
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
BANNERS_DIR = FRONTEND_DIR / "banners"

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
if BANNERS_DIR.exists():
    app.mount("/banners", StaticFiles(directory=str(BANNERS_DIR)), name="banners")

# ==========================
# 🚀 Główne endpointy
# ==========================
app.include_router(documents_router, prefix="/documents")

@app.get("/")
async def root():
    frontend_url = os.getenv("FRONTEND_URL", "https://storage.googleapis.com/smartdocfinder-frontend/index.html")
    return {
        "message": "🚀 SmartDocFinder API is running",
        "frontend": frontend_url
    }