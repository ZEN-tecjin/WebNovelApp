import os
from urllib.parse import urljoin, urlparse

def _safe_requests_get(url, headers=None, timeout=10):
    # Local helper: import inside function to avoid import-time errors if requests missing.
    import requests
    default_headers = {
        "User-Agent": "WebNovelApp/1.0 (+https://example.com)"
    }
    if headers:
        default_headers.update(headers)
    resp = requests.get(url, headers=default_headers, timeout=timeout)
    resp.raise_for_status()
    return resp

def _get_soup(html):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser")

def download_novel(url, max_chapters=20):
    """
    High-level function:
    - Fetches the provided URL
    - Attempts to find chapter links (heuristic)
    - Downloads up to `max_chapters` chapters and delegates saving to storage.save_chapter
    """
    print(f"Starting download for: {url}")
    try:
        resp = _safe_requests_get(url)
    except Exception as e:
        print(f"Network error when fetching {url}: {e}")
        return

    soup = _get_soup(resp.text)

    # Heuristic: collect <a> tags that likely point to chapters.
    anchors = soup.find_all("a", href=True)
    candidate_links = []
    for a in anchors:
        text = (a.get_text() or "").strip().lower()
        href = a["href"]
        # common signals: "chapter", "ch.", "ch ", "vol", numbers in text
        if "chapter" in text or "ch " in text or "ch." in text or "vol" in text:
            candidate_links.append(urljoin(url, href))
        else:
            # sometimes link text is just a number
            if text.isdigit() and len(text) <= 4:
                candidate_links.append(urljoin(url, href))

    # Deduplicate while preserving order
    seen = set()
    chapters = []
    for link in candidate_links:
        if link not in seen:
            seen.add(link)
            chapters.append(link)
        if len(chapters) >= max_chapters:
            break

    # Fallback: if no candidate chapters found, try to treat page itself as single chapter
    if not chapters:
        print("No chapter links found heuristically; treating the provided URL as a single chapter.")
        chapters = [url]

    # Lazy import storage to avoid circular issues
    from storage import save_chapter, make_novel_folder

    novel_title = _guess_title(soup, url)
    base_folder = make_novel_folder(novel_title)
    print(f"Detected novel title: {novel_title} -> saving in: {base_folder}")

    for idx, chap_url in enumerate(chapters, start=1):
        print(f"Fetching chapter {idx}: {chap_url}")
        try:
            r = _safe_requests_get(chap_url)
            s = _get_soup(r.text)
            # Extract main text: attempt a few heuristics
            content = _extract_text_from_soup(s)
            chap_title = _guess_chapter_title(s) or f"Chapter_{idx}"
            save_chapter(base_folder, chap_title, content)
            print(f"Saved: {chap_title}")
        except Exception as e:
            print(f"Failed to fetch/save chapter at {chap_url}: {e}")

def _guess_title(soup, url):
    # Prefer <meta property="og:title">, then <title>, then hostname as fallback
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        return meta["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    parsed = urlparse(url)
    return parsed.hostname or "novel"

def _guess_chapter_title(soup):
    # Try common header tags
    for tag in ("h1", "h2", "h3"):
        el = soup.find(tag)
        if el and el.get_text().strip():
            return el.get_text().strip()
    return None

def _extract_text_from_soup(soup):
    """
    Heuristics to pull readable text:
    - Look for elements with class names containing 'chapter', 'content', 'entry', 'post'
    - Fallback: join all <p> text
    """
    selectors = []
    # find by id/class hints
    for hint in ("chapter", "content", "post", "entry", "main", "novel"):
        selectors.extend(soup.find_all(attrs={"class": lambda v: v and hint in v.lower()}))
        selectors.extend(soup.find_all(attrs={"id": lambda v: v and hint in v.lower()}))

    # If any selector elements found, prefer those
    if selectors:
        texts = []
        for el in selectors:
            ps = el.find_all("p")
            if ps:
                for p in ps:
                    texts.append(p.get_text().strip())
            else:
                txt = el.get_text().strip()
                if txt:
                    texts.append(txt)
        return "\\n\\n".join(t for t in texts if t)

    # fallback: join all <p>
    ps = soup.find_all("p")
    if ps:
        return "\\n\\n".join(p.get_text().strip() for p in ps if p.get_text().strip())

    # last resort: raw text
    return soup.get_text(separator="\\n").strip()
