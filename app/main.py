from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes import documents

app = FastAPI(title="SmartDocFinder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API router under /documents
app.include_router(documents.router, prefix="/documents")

# serve banners and frontend static files
app.mount("/banners", StaticFiles(directory="banners"), name="banners")
# serve frontend files (index.html, style.css, script.js)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")