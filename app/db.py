from pathlib import Path
import sqlite3
from datetime import datetime

DB_PATH = Path(__file__).parent / "documents.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # create table if missing (with filepath column)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            filepath TEXT,
            uploaded_at TEXT
        )
    """)
    conn.commit()

    # ensure 'filepath' column exists (for old DBs)
    cur.execute("PRAGMA table_info(documents)")
    cols = [row[1] for row in cur.fetchall()]
    if "filepath" not in cols:
        try:
            cur.execute("ALTER TABLE documents ADD COLUMN filepath TEXT")
            conn.commit()
        except Exception:
            # if alter fails, ignore (rare)
            pass

    conn.close()

def add_document(filename: str, filepath: Path):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO documents (filename, filepath, uploaded_at)
        VALUES (?, ?, ?)
    """, (filename, str(filepath), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_all_documents():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT filename, filepath FROM documents ORDER BY uploaded_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"filename": r[0], "filepath": r[1]} for r in rows]

def get_document_by_filename(filename: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT filename, filepath FROM documents WHERE filename = ?", (filename,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"filename": row[0], "filepath": row[1]}
    return None

def delete_document(filename: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM documents WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()