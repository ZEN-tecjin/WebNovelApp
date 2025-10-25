import os
import re
import json
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path.cwd() / "novels"
DB_PATH = Path.cwd() / "novels.db"

def _safe_name(name):
    name = re.sub(r"[\\/:*?<>|]+", "_", name)
    return name.strip()[:200] or "untitled"

def make_novel_folder(novel_title):
    novel_folder = BASE_DIR / _safe_name(novel_title)
    novel_folder.mkdir(parents=True, exist_ok=True)
    return str(novel_folder)

# ---------- DATABASE SETUP ----------
def init_db():
    """Create the SQLite DB if not exists."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            novel_title TEXT,
            chapter_title TEXT,
            last_line INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def update_progress(novel_title, chapter_title, line_number):
    """Save or update progress for a specific chapter."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO progress (novel_title, chapter_title, last_line, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(novel_title, chapter_title)
        DO UPDATE SET last_line=?, updated_at=?;
    """, (novel_title, chapter_title, line_number, datetime.now().isoformat(),
          line_number, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_progress(novel_title, chapter_title):
    """Return last line read for a chapter (if any)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT last_line FROM progress
        WHERE novel_title=? AND chapter_title=?
    """, (novel_title, chapter_title))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

# ---------- METADATA & FILE SAVING ----------
def save_metadata(novel_folder, metadata):
    """Writes metadata.json inside the novel folder."""
    meta_path = Path(novel_folder) / "metadata.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    return str(meta_path)

def load_metadata(novel_folder):
    """Loads metadata.json if present."""
    meta_path = Path(novel_folder) / "metadata.json"
    if meta_path.exists():
        with meta_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"chapters": []}

def save_chapter(novel_folder, chapter_title, text, source_url=None, fmt="txt"):
    """
    Saves a chapter to disk and updates metadata.json.
    fmt: choose between 'txt', 'md', or 'html'
    """
    ext = fmt.lower()
    if ext not in ("txt", "md", "html"):
        ext = "txt"

    novel_folder = Path(novel_folder)
    novel_folder.mkdir(parents=True, exist_ok=True)
    fname = _safe_name(chapter_title) + f".{ext}"
    fpath = novel_folder / fname

    # Save chapter text
    with fpath.open("w", encoding="utf-8") as f:
        f.write(text or "")

    # Load existing metadata
    metadata = load_metadata(novel_folder)
    if "title" not in metadata:
        metadata["title"] = novel_folder.name
    if "source_url" not in metadata and source_url:
        metadata["source_url"] = source_url
    if "chapters" not in metadata:
        metadata["chapters"] = []

    # Avoid duplicates
    if not any(c["title"] == chapter_title for c in metadata["chapters"]):
        metadata["chapters"].append({
            "title": chapter_title,
            "file": fname,
            "added": datetime.now().isoformat()
        })

    save_metadata(novel_folder, metadata)
    return str(fpath)

def list_chapters():
    """Returns a flattened list of all saved chapters."""
    if not BASE_DIR.exists():
        return []
    chapters = []
    for novel_dir in sorted(BASE_DIR.iterdir()):
        if novel_dir.is_dir():
            meta = load_metadata(novel_dir)
            for c in meta.get("chapters", []):
                chapters.append(str(novel_dir / c["file"]))
    return chapters
