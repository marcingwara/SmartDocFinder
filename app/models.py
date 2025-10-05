# simple sqlite helper using sqlite3
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

DB_PATH = Path("db.sqlite")

def get_conn():
       conn = sqlite3.connect(DB_PATH)
       conn.row_factory = sqlite3.Row
       return conn

def init_db():
       DB_PATH.parent.mkdir(parents=True, exist_ok=True)
       conn = get_conn()
       cur = conn.cursor()
       cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL UNIQUE,
        filepath TEXT NOT NULL,
        content TEXT,
        created_at TEXT NOT NULL
    )
    """)
       conn.commit()
       conn.close()

def add_document(filename: str, filepath: str, content: str):
       conn = get_conn()
       cur = conn.cursor()
       cur.execute("""
    INSERT OR REPLACE INTO documents (filename, filepath, content, created_at)
    VALUES (?, ?, ?, ?)
    """, (filename, filepath, content, datetime.utcnow().isoformat()))
       conn.commit()
       conn.close()

def list_documents() -> List[Dict]:
       conn = get_conn()
       cur = conn.cursor()
       cur.execute("SELECT id, filename, filepath, substr(content,1,500) as preview, created_at FROM documents ORDER BY created_at DESC")
       rows = [dict(r) for r in cur.fetchall()]
       conn.close()
       return rows

def get_document_by_filename(filename: str) -> Optional[Dict]:
       conn = get_conn()
       cur = conn.cursor()
       cur.execute("SELECT id, filename, filepath, content, created_at FROM documents WHERE filename = ?", (filename,))
       r = cur.fetchone()
       conn.close()
       return dict(r) if r else None

def delete_document_by_filename(filename: str) -> bool:
       conn = get_conn()
       cur = conn.cursor()
       cur.execute("DELETE FROM documents WHERE filename = ?", (filename,))
       changed = cur.rowcount
       conn.commit()
       conn.close()
       return changed > 0

def search_documents(query: str) -> List[Dict]:
       conn = get_conn()
       cur = conn.cursor()
       # basic case-insensitive substring search
       likeq = f"%{query}%"
       cur.execute("SELECT id, filename, filepath, instr(lower(content), lower(?)) as found_pos, substr(content, instr(lower(content), lower(?)) , 500) as snippet FROM documents WHERE lower(content) LIKE lower(?)", (query, query, likeq))
       rows = [dict(r) for r in cur.fetchall()]
       conn.close()
       return rows