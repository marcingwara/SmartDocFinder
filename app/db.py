import sqlite3
from pathlib import Path
from datetime import datetime

DB_FILE = Path(__file__).parent / "documents.db"

def get_conn():
    conn = sqlite3.connect(str(DB_FILE))
    return conn

def init_db():
    conn = get_conn()
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

def add_document(filename: str, filepath: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO documents (filename, filepath, uploaded_at) VALUES (?, ?, ?)",
        (filename, str(filepath), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def list_documents():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT filename, filepath, uploaded_at FROM documents ORDER BY uploaded_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"filename": r[0], "filepath": r[1], "uploaded_at": r[2]} for r in rows]

def get_document(filename: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT filename, filepath, uploaded_at FROM documents WHERE filename = ?", (filename,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"filename": row[0], "filepath": row[1], "uploaded_at": row[2]}
    return None

def delete_document(filename: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM documents WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()

# initialize DB on import
init_db()