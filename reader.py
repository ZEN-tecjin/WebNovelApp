from pathlib import Path

def read_chapter(path, lines_per_page=20):
    path = Path(path)
    if not path.exists():
        print(f"Chapter file not found: {path}")
        return
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    total = len(lines)
    pos = 0
    while pos < total:
        chunk = lines[pos:pos+lines_per_page]
        print("".join(chunk))
        pos += lines_per_page
        if pos < total:
            cmd = input("[Enter] next page, (q)uit: ").strip().lower()
            if cmd == "q":
                break
