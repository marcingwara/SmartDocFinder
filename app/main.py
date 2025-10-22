import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.routes.documents import router as documents_router

# ✅ Bezpieczne ładowanie bazy danych
try:
    from app import db
    db.cleanup_missing_files()
except Exception as e:
    print(f"⚠️ Database initialization skipped: {e}")

# ========================================
# 🚀 FastAPI app initialization
# ========================================
app = FastAPI(title="SmartDocFinder API")

# ========================================
# 🔒 CORS – pozwól tylko frontowi z Cloud Storage
# ========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://storage.googleapis.com",
        "https://storage.googleapis.com/smartdocfinder-frontend",
        "https://smartdocfinder-861730700785.europe-west1.run.app",  # Cloud Run self-origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# 📁 Ścieżki frontend + bannery
# ========================================
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
BANNERS_DIR = FRONTEND_DIR / "banners"

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
if BANNERS_DIR.exists():
    app.mount("/banners", StaticFiles(directory=str(BANNERS_DIR)), name="banners")

# ========================================
# 🔗 Główne trasy /documents/*
# ========================================
app.include_router(documents_router, prefix="/documents")

# ========================================
# 🩺 Endpoint zdrowia (dla Cloud Run)
# ========================================
@app.get("/health")
def health():
    return {"status": "ok"}

# ========================================
# 🏁 Root endpoint – pokazuje link do frontendu
# ========================================
@app.get("/")
async def root():
    frontend_url = os.getenv(
        "FRONTEND_URL",
        "https://storage.googleapis.com/smartdocfinder-frontend/index.html"
    )
    return {
        "message": "🚀 SmartDocFinder API is running",
        "frontend": frontend_url
    }