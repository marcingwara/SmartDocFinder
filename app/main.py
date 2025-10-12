from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes.documents import router as documents_router
from pathlib import Path

app = FastAPI(title="SmartDocFinder API")

# === CORS dla frontendu ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # w razie potrzeby dodaj np. http://localhost:5500
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Ścieżki ===
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
BANNERS_DIR = FRONTEND_DIR / "banners"

# === Serwowanie plików statycznych ===
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
app.mount("/banners", StaticFiles(directory=str(BANNERS_DIR)), name="banners")

# === Rejestracja routerów ===
app.include_router(documents_router)

# === Strona główna ===
@app.get("/")
async def root():
    return {
        "message": "🚀 SmartDocFinder API is running",
        "frontend": "http://127.0.0.1:8000/frontend/index.html"
    }