"""
Extract SGO names from HTML pages using BeautifulSoup.

Install: pip install beautifulsoup4
"""
from models import SGO

try:
    from bs4 import BeautifulSoup
except ImportError as e:
    raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4") from e

MAX_BYTES = 50_000_000


def parse_html_table(html: str, state: str, url: str) -> list[SGO]:
    """
    Find the first <table> on the page and extract one SGO per row.

    Assumes the first column of each non-header row is the org name.
    Skips the header row if the first cell text matches a known header word.
    """
    if len(html.encode()) > MAX_BYTES:
        raise ValueError(f"HTML from {url} exceeds size limit")

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        raise ValueError(f"No <table> found in HTML from {url} — try parse_html_list instead")

    HEADER_WORDS = {"name", "organization", "sgo", "scholarship", "no.", "#", "entity"}
    results = []

    for row in table.find_all("tr"):
        cells = [td.get_text(separator=" ", strip=True) for td in row.find_all(["td", "th"])]
        if not cells:
            continue
        first = cells[0]
        if first.lower() in HEADER_WORDS or first.lower().startswith("name"):
            continue
        try:
            results.append(SGO(state=state, name=first, ein=None, raw_source=url))
        except ValueError:
            pass

    if not results:
        raise ValueError(f"No SGO names extracted from HTML table: {url}")

    return results


def parse_html_list(html: str, state: str, url: str) -> list[SGO]:
    """
    Extract SGO names from <li> or <a> elements when there is no table.

    Useful for pages that present orgs as a bulleted list or link directory.
    """
    if len(html.encode()) > MAX_BYTES:
        raise ValueError(f"HTML from {url} exceeds size limit")

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Prefer <li> items; fall back to plain <a> links if nothing found
    candidates = soup.find_all("li") or soup.find_all("a")

    for tag in candidates:
        text = tag.get_text(separator=" ", strip=True)
        try:
            results.append(SGO(state=state, name=text, ein=None, raw_source=url))
        except ValueError:
            pass

    if not results:
        raise ValueError(f"No SGO names extracted from HTML list: {url}")

    return results
