# scraper.py (fixed & improved)
import os
import time
import random
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from requests_html import HTMLSession
from playwright.sync_api import sync_playwright

# ---------- helpers ----------

def _safe_requests_get(url, headers=None, timeout=15):
    """Request a page with polite headers. Returns requests.Response or None."""
    import requests
    default_headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/117.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
            "Gecko/20100101 Firefox/117.0",
        ]),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": url,
    }
    if headers:
        default_headers.update(headers)
    try:
        resp = requests.get(url, headers=default_headers, timeout=timeout)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return None

def _render_js_page(url):
    """Render a webpage with Playwright and return the full HTML."""
    html = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/118.0 Safari/537.36"
            })
            print(f"[Playwright] Rendering {url} ...")
            page.goto(url, timeout=30000)
            page.wait_for_timeout(5000)  # wait 5s for JS to load
            html = page.content()
            browser.close()
    except Exception as e:
        print(f"⚠️ Playwright failed to render {url}: {e}")
    return html


def _get_soup(html):
    """Return BeautifulSoup object from HTML string, or None if invalid."""
    from bs4 import BeautifulSoup
    if not isinstance(html, (str, bytes)):
        return None
    return BeautifulSoup(html, "html.parser")

def _save_debug_html(novel_folder, idx, html):
    """Write raw html to a file for debugging / adapter creation."""
    try:
        p = Path(novel_folder) / f"raw_chapter_{idx}.html"
        p.write_text(html or "", encoding="utf-8")
        print(f"  (Saved debug HTML -> {p})")
    except Exception as e:
        print(f"  (Failed to save debug html: {e})")


# ---------- main function ----------

def download_novel(url, max_chapters=20, render_js=False):
    """High-level: find chapter links from index page, then download each chapter."""
    print(f"Starting download for: {url}")

    domain = urlparse(url).netloc.lower()
    chapters = None
    resp = _safe_requests_get(url)
    if not resp:
        print("❌ Failed to get novel index page.")
        return

    soup_index = _get_soup(resp.text)
    if soup_index is None:
        print("❌ Failed to parse main page HTML.")
        return
    if "novelight" in domain:
        chapters = adapter_novellight(soup_index, url)
    if not chapters:
        chapters = get_chapter_links(soup_index, url)



    # Use the robust TOC extractor
    chapters = get_chapter_links(soup_index, url)
    if not chapters:
        print("⚠️ No chapters found — treating as single-page novel.")
        chapters = [url]

    # Prepare saving
    from storage import save_chapter, make_novel_folder
    novel_title = _guess_title(soup_index, url)
    base_folder = make_novel_folder(novel_title)
    print(f"📘 Detected novel title: {novel_title}")
    print(f"📁 Saving chapters in: {base_folder}")

    # download loop
    for idx, chap_url in enumerate(chapters, start=1):
        print(f"\n🔹 Fetching chapter {idx}: {chap_url}")
        time.sleep(2)  # polite delay

        # 1) Try fast GET
        r = _safe_requests_get(chap_url)
        html = r.text if r else ""

        # 2) If html looks incomplete, try JS render
        if not html or len(html) < 400 or any(k in html.lower() for k in ("loading", "subscribe", "table of contents")):
            print(" -> page looks incomplete, trying JS renderer...")
            html = _render_js_page(chap_url)

        if not html:
            print(" -> failed to get HTML for", chap_url)
            _save_debug_html(base_folder, idx, html)
            continue

        s = _get_soup(html)
        if not s:
            print(" -> BeautifulSoup failed to parse HTML; saving debug copy.")
            _save_debug_html(base_folder, idx, html)
            continue

        # extract and save
        content = _extract_text_from_soup(s)
        if not content or len(content) < 100:
            print(" -> extracted content is small; saving raw HTML for inspection.")
            _save_debug_html(base_folder, idx, html)
            # still attempt to save a stub so user can see file exists
        chap_title = _guess_chapter_title(s) or f"Chapter_{idx}"
        try:
            save_chapter(base_folder, chap_title, content)
            print(f"✅ Saved: {chap_title}")
        except Exception as e:
            print(f"❌ Save failed for {chap_url}: {e}")
            _save_debug_html(base_folder, idx, html)


# ---------- parsing helpers ----------

def _guess_title(soup, url):
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        return meta["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return urlparse(url).hostname or "novel"

def _guess_chapter_title(soup):
    for tag in ("h1", "h2", "h3"):
        el = soup.find(tag)
        if el and el.get_text().strip():
            return el.get_text().strip()
    return None

def _extract_text_from_soup(soup):
    candidates = []
    for hint in (
        "chapter-content", "chapter-body", "entry-content",
        "post-content", "reading-content", "text-left", "reader-content", "chapterText", "novel-body"
    ):
        candidates.extend(soup.find_all(attrs={"class": lambda v: v and hint in v.lower()}))
        candidates.extend(soup.find_all(attrs={"id": lambda v: v and hint in v.lower()}))

    if not candidates:
        for div in soup.find_all("div"):
            text = div.get_text(separator="\n").strip()
            if len(text.split()) > 100:
                candidates.append(div)

    best_block = ""
    for el in candidates:
        text = el.get_text(separator="\n").strip()
        if len(text) > len(best_block):
            best_block = text

    if best_block:
        cleaned = []
        for line in best_block.splitlines():
            line = line.strip()
            if not line:
                continue
            if any(x in line.lower() for x in ["support us", "bookmark", "previous", "next", "table of contents", "loading"]):
                continue
            cleaned.append(line)
        return "\n\n".join(cleaned)

    paragraphs = soup.find_all("p")
    if paragraphs:
        return "\n\n".join(p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20)

    return soup.get_text(separator="\n").strip()

# CHAPTER TOC HINTS & extractor

CHAPTER_HINTS = (
    "chapter-list", "chapter-listing", "chapter-list-wrap",
    "chapters", "chapter", "toc", "table-of-contents",
    "chapter__list", "list-chapters", "chapter-row"
)

def get_chapter_links(soup, base_url):
    """Return an ordered list of chapter URLs (best effort)."""
    links = []

    # 1) Try containers with common class/id hints
    for hint in CHAPTER_HINTS:
        containers = soup.find_all(attrs={"class": lambda v: v and hint in v.lower()})
        containers += soup.find_all(attrs={"id": lambda v: v and hint in v.lower()})
        for c in containers:
            for a in c.find_all("a", href=True):
                links.append(urljoin(base_url, a["href"]))
        if links:
            return _dedupe_preserve_order(links)

    # 2) Fallback: heuristics across all anchors
    candidate = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = (a.get_text() or "").strip()
        abs_url = urljoin(base_url, href)
        if re.search(r"/chapter[s]?/|chapter[-_]?\d+", href, re.I) or "chapter" in text.lower():
            candidate.append(abs_url)
        else:
            if re.search(r"/\d{1,6}(/)?$", href):
                candidate.append(abs_url)

    return _dedupe_and_sort_chapter_urls(candidate)

def _dedupe_preserve_order(seq):
    seen = set()
    out = []
    for u in seq:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def _dedupe_and_sort_chapter_urls(urls):
    urls = _dedupe_preserve_order(urls)
    def keyfn(u):
        m = re.search(r"(?:chapter[-_/]?)(\d+)", u, re.I)
        if m:
            return int(m.group(1))
        m2 = re.findall(r"(\d+)", u)
        if m2:
            return int(m2[-1])
        return u
    try:
        return sorted(urls, key=keyfn)
    except Exception:
        return urls

# Example adapter placeholder (fill selector after inspecting site)
def adapter_novellight(soup, base_url):
    """Extract chapter links from NovelLight's chapter list."""
    toc = soup.select_one("div.chapter-list")
    if not toc:
        toc = soup.select_one("div.list-chapter")  # fallback
    if not toc:
        return None
    links = [urljoin(base_url, a["href"]) for a in toc.select("a[href]")]
    return _dedupe_and_sort_chapter_urls(links)
