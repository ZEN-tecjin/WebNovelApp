from pathlib import Path
import json
import pyttsx3

BOOKMARK_FILE = Path("bookmarks.json")


def _load_bookmarks():
    """Load saved bookmarks (JSON Files)"""
    if BOOKMARK_FILE.exists():
        with BOOKMARK_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_bookmarks(data):
    """Save saved bookmarks (JSON Files)"""
    with BOOKMARK_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def _save_progress(chapter_path, line_number):
    """Save the current reading position for a chapter."""
    bookmarks = _load_bookmarks()
    bookmarks[str(chapter_path)] = line_number
    _save_bookmarks(bookmarks)

def _get_progress(chapter_path):
    """ Retrieve saved progress for a chapter."""
    bookmarks = _load_bookmarks()
    return bookmarks.get(str(chapter_path), 0)

def search_text(chapter_path, keyword):
    """Find all lines containing the given keyword."""
    chapter_path = Path(chapter_path)
    if not chapter_path.exists():
        print("File not found.")
        return []
    with chapter_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    matches = [(i+ 1, line.strip())for i, line in enumerate(lines) if keyword.lower in line.lower()]

    if not matches:
        print(f"No matches found for '{keyword}'.")
    else:
        print(f"Found {len(matches)} results for '{keyword}'.\n")
        for line_num, text in matches[:10]: # Show up to 10
            print(f"[Line {line_num}] {text}")
    return matches


def tts_read(text):
    """Read text aloud using pyttsx3."""
    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    engine.say(text)
    engine.runAndWait()

def read_chapter(path, lines_per_page=20, return_text=False):
    """
    Read a chapter page by page
    - Supports bookmark saving.
    - Allow TTS reading(means you have a voice recording to read your novel)
    - Allow keyword search.
    """
    path = Path(path)
    if not path.exists():
        print(f"Chapter file not found: {path}")
        return "File not found." if return_text else None

    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    total = len(lines)
    pos = _get_progress(path) # Start from last position
    print(f"Resuming at line {pos} of {total}")

    while pos < total:
        chunk = lines[pos:pos + lines_per_page]
        content = "".join(chunk)
        if return_text:
            return content
        print(content)

        cmd = input("[Enter] next, (s)earch, (t)ts, (q)quit: ").strip().lower()
        if cmd == "q":
            _save_progress(path, pos)
            print(f"Progress saved at line{pos}.")
            break
        elif cmd == "s":
            keyword = input("Enter keyword: ").strip()
            if keyword:
                search_text(path, keyword)
        elif cmd == "t":
            tts_read(content)
        else:
            pos += lines_per_page

    if pos >= total:
        print("End of chapter reached.")
        _save_progress(path, 0) #Reset bookmark if finished.


