
import random
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from storage import make_novel_folder, save_chapter
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
            try:
                page.goto(url, timeout=30000)
                page.wait_for_selector("#chr-content", timeout=10000)
            except Exception:
                page.wait_for_timeout(5000)

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

def download_chapters(chapter_pairs, novel_title=None, base_folder=None, render_js=False, window=None):
    """
    Download a list of (chapter_title, chapter_url).
    If novel_title or base_folder not provided, guess from the first chapter page.
    Saves both cleaned HTML and extracted text (txt).
    """


    if not chapter_pairs:
        print("No chapters to download.")
        return

    # If novel_title not provided, try to guess from the first chapter page
    first_title, first_url = chapter_pairs[0]
    if base_folder is None:
        # attempt to fetch index/title from first_url's parent
        resp = _safe_requests_get(first_url)
        if resp:
            soup = _get_soup(resp.text)
            novel_title = novel_title or _guess_title(soup, first_url)
        else:
            novel_title = novel_title or "novel"
        base_folder = make_novel_folder(novel_title)

    total = len(chapter_pairs)
    print(f"📘 {novel_title} — downloading {total} chapters")

    for idx, (chap_title, chap_url) in enumerate(chapter_pairs, start=1):
        status_msg = f"Downloading chapter {idx}/{total} - {chap_title}"
        print(status_msg)
        if window:
            window["-STATUS-"].update(status_msg)
            window["-PROGRESS-"].update(int(idx / total * 100))
            window.refresh()

        r = _safe_requests_get(chap_url)
        html = r.text if r else ""
        # decide whether to render JS
        if render_js or (not html or "loading" in html.lower() or "comment" in html.lower()):
            html = _render_js_page(chap_url)

        if not html:
            print(f"No html for {chap_url}")
            continue


        s = _get_soup(html)
        if not s:
            continue

        content_text = _extract_text_from_soup(s) or ""
        if not content_text.strip():
            print(f"Empty chapter body for {chap_title}")
            continue

        content_text = _extract_text_from_soup(s) or ""
        cleaned_html_str = _clean_html_for_save(_get_soup(html))

        # Save: html and text
        save_chapter(base_folder, chap_title, cleaned_html_str, source_url=chap_url, fmt="html")
        save_chapter(base_folder, chap_title, content_text, source_url=chap_url, fmt="txt")

        # optional: save raw html for debugging (keeps original)
        _save_debug_html(base_folder, idx, html)

    if window:
        window["-STATUS-"].update(f"✅ Finished downloading {total} chapters!")
        window["-PROGRESS-"].update(100)
        window.refresh()
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

def _clean_html_for_save(soup):
    if soup is None:
        return ""
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    return str(soup)



def _extract_text_from_soup(soup):
    main = soup.find("div", id = "chr-content")
    if main:
        for t in main(["script", "style","noscript", "aside"]):
            t.decompose()
        paragraphs = main.find_all(["p"])
        if paragraphs:
            text = "\n\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
            return text.strip()

    for hint in (
         "chapter-content", "chapter-body", "entry-content",
        "post-content", "reading-content", "reader-content", "chaptertext", "novel-body"
    ):
        block = soup.find(attrs ={"class": lambda v: v and hint in v.lower()})
        if block:
            text = block.get_text(seperator = "\n").strip()
            if text:
                return text

    divs = soup.find_all("div")
    longest = ""
    for d in divs:
        t = d.get_text(separator ="\n").strip()
        if len(t) > len(longest):
            longest = t
    return longest.strip()

# CHAPTER TOC HINTS & extractor

CHAPTER_HINTS = (
    "chapter-list", "chapter-listing", "chapter-list-wrap",
    "chapters", "chapter", "toc", "table-of-contents",
    "chapter__list", "list-chapters", "chapter-row"
)

def get_chapter_list(url, render_js=False):
    """
    Given a novel index/TOC url, return a list of (chapter_title, chapter_url)
    in chronological order (chapter 1 first).
    Best-effort extraction: site-specific (novelight) first, fallback to heuristics.
    """
    resp = _safe_requests_get(url)
    if not resp:
        print(f"Failed to fetch TOC: {url}")
        return []

    soup = _get_soup(resp.text)
    if not soup:
        return []

    domain = urlparse(url).netloc.lower()
    pairs = []

    # site-specific: NovelLight's TOC often contains anchor text with chapter titles
    if "novelight" in domain:
        toc = soup.select_one("div.chapter-list") or soup.select_one("div.list-chapter")
        if toc:
            anchors = toc.select("a[href]")
            # anchors are typically newest->oldest on the site, so reverse to get chronological
            anchors = list(reversed(anchors))
            for a in anchors:
                href = a.get("href")
                if not href:
                    continue
                title = (a.get_text() or "").strip() or None
                pairs.append((title or href.split("/")[-1], urljoin(url, href)))
            return pairs

    # Generic fallback: try to obtain anchors by hints from get_chapter_links
    # Find containers matching CHAPTER_HINTS and extract (text, href)
    for hint in CHAPTER_HINTS:
        containers = soup.find_all(attrs={"class": lambda v: v and hint in v.lower()})
        containers += soup.find_all(attrs={"id": lambda v: v and hint in v.lower()})
        if containers:
            links = []
            for c in containers:
                for a in c.find_all("a", href=True):
                    title = (a.get_text() or "").strip()
                    href = urljoin(url, a["href"])
                    links.append((title or href.split("/")[-1], href))
            if links:
                # preserve order from page, but try to sort numerically when we can
                # attempt to sort by number if present in href (chapterX)
                def num_key(pair):
                    u = pair[1]
                    m = re.search(r"(?:chapter[-_/ ]?)(\d+)", u, re.I)
                    if m:
                        return int(m.group(1))
                    m2 = re.findall(r"(\d+)", u)
                    if m2:
                        return int(m2[-1])
                    return 0
                try:
                    return sorted(links, key=num_key)
                except Exception:
                    return links

    # Last resort: gather anchors across whole page that look like chapter links
    anchors = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = (a.get_text() or "").strip()
        abs_url = urljoin(url, href)
        if re.search(r"/chapter[s]?/|chapter[-_]?\d+", href, re.I) or "chapter" in text.lower():
            anchors.append((text or abs_url.split("/")[-1], abs_url))
        else:
            if re.search(r"/\d{1,6}(/)?$", href):
                anchors.append((text or abs_url.split("/")[-1], abs_url))
    # dedupe preserve order
    out = []
    seen = set()
    for t,u in anchors:
        if u not in seen:
            seen.add(u)
            out.append((t or u.split("/")[-1], u))
    # try sorting numerically if possible
    def fallback_key(pair):
        u = pair[1]
        m2 = re.findall(r"(\d+)", u)
        if m2:
            return int(m2[-1])
        return 0
    try:
        return sorted(out, key=fallback_key)
    except:
        return out

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
        m = re.search(r"chapter[-_/]*(\d+)", u, re.I)
        if m:
            return int(m.group(1))
        m2 = re.findall(r"(\d+)", u)
        if m2:
            return int(m2[-1])
        return u
    try:
        return sorted(urls, key=keyfn)
    except Exception as e:
        print(f"Sorting failed: {e}")
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

    links = _dedupe_and_sort_chapter_urls(links)

    links.reverse()

    return links
