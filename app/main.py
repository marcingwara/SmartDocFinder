from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes.documents import router as documents_router
from pathlib import Path
import os

app = FastAPI(title="SmartDocFinder API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
BANNERS_DIR = FRONTEND_DIR / "banners"

# Static files mounting
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
if BANNERS_DIR.exists():
    app.mount("/banners", StaticFiles(directory=str(BANNERS_DIR)), name="banners")

# Routers
app.include_router(documents_router)

@app.get("/")
async def root():
    return {
        "message": "🚀 SmartDocFinder API is running",
        "frontend": "http://127.0.0.1:8000/frontend/index.html"
    }