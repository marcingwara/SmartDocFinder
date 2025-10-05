from fastapi import FastAPI
from app.routes import documents

app = FastAPI(title="SmartDocFinder")
# include router under /documents
app.include_router(documents.router, prefix="/documents")