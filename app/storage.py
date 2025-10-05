import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# JSON file to store metadata
METADATA_FILE = Path("uploaded_pdfs/metadata.json")

# Ensure directory exists
METADATA_FILE.parent.mkdir(exist_ok=True)

def load_metadata() -> List[Dict]:
    """Load metadata from JSON file"""
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_metadata(data: List[Dict]):
    """Save metadata to JSON file"""
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_metadata(filename: str, num_pages: int, size_kb: float):
    """Add new PDF metadata"""
    metadata = load_metadata()
    new_entry = {
        "filename": filename,
        "pages": num_pages,
        "size_kb": round(size_kb, 2),
        "uploaded_at": datetime.now().isoformat()
    }
    metadata.append(new_entry)
    save_metadata(metadata)

def get_metadata(filename: str):
    """Return metadata for a specific file"""
    metadata = load_metadata()
    for item in metadata:
        if item["filename"] == filename:
            return item
    return None

def delete_metadata(filename: str):
    """Remove metadata entry"""
    metadata = [m for m in load_metadata() if m["filename"] != filename]
    save_metadata(metadata)