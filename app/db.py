import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "documents.db"   # persistent file in project

def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            filepath TEXT,
            uploaded_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize on import
init_db()

def add_document(filename: str, filepath: Path):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO documents (filename, filepath, uploaded_at) VALUES (?, ?, ?)",
        (filename, str(filepath), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def list_documents():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT filename, filepath, uploaded_at FROM documents ORDER BY uploaded_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_document(filename: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT filename, filepath, uploaded_at FROM documents WHERE filename = ?", (filename,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_document(filename: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM documents WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()

def cleanup_missing_files():
    """
    Usuwa z bazy wpisy dla plików, które nie istnieją fizycznie
    w katalogu uploaded_pdfs/.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT filename, filepath FROM documents")
    rows = cur.fetchall()
    removed = 0

    for row in rows:
        filename = row["filename"]
        filepath = Path(row["filepath"])
        if not filepath.exists():
            cur.execute("DELETE FROM documents WHERE filename = ?", (filename,))
            removed += 1

    conn.commit()
    conn.close()
    print(f"🧹 Cleanup complete — removed {removed} missing files from database.")