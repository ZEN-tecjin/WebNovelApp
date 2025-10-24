import os
import re
from pathlib import Path

BASE_DIR = Path.cwd() / "novels"

def _safe_name(name):
    # create a filesystem-friendly name
    name = re.sub(r"[\\\\/:*?<>|]+", "_", name)
    return name.strip()[:200] or "untitled"

def make_novel_folder(novel_title):
    novel_folder = BASE_DIR / _safe_name(novel_title)
    novel_folder.mkdir(parents=True, exist_ok=True)
    return str(novel_folder)

def save_chapter(novel_folder, chapter_title, text):
    novel_folder = Path(novel_folder)
    novel_folder.mkdir(parents=True, exist_ok=True)
    fname = _safe_name(chapter_title) + ".txt"
    fpath = novel_folder / fname
    with fpath.open("w", encoding="utf-8") as f:
        f.write(text or "")
    return str(fpath)

def list_chapters():
    """
    Returns a flattened list of available chapter file paths under ./novels,
    sorted by filename.
    """
    if not BASE_DIR.exists():
        return []
    chapters = []
    for novel_dir in sorted(BASE_DIR.iterdir()):
        if novel_dir.is_dir():
            for file in sorted(novel_dir.iterdir()):
                if file.suffix.lower() == ".txt":
                    chapters.append(str(file))
    return chapters
