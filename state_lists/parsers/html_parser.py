"""
Extract SGO names from HTML pages using BeautifulSoup.

Install: pip install beautifulsoup4
"""
import re
from models import SGO

_HTML_COL_ALIASES: dict[str, list[str]] = {
    "name":    ["organization name", "name", "sgo name", "sto name", "organization"],
    "ein":     ["ein", "federal tax id", "tax id", "fein"],
    "address": ["address", "business address", "mailing address", "street address"],
    "phone":   ["telephone", "phone", "phone number"],
    "email":   ["e-mail", "email"],
    "website": ["web-site", "website", "url", "web address", "sto website"],
}


def _col_index(headers: list[str], aliases: list[str]) -> int | None:
    hl = [h.strip().lower() for h in headers]
    for alias in aliases:
        if alias in hl:
            return hl.index(alias)
    return None

try:
    from bs4 import BeautifulSoup
except ImportError as e:
    raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4") from e

MAX_BYTES = 50_000_000


def parse_html_table(html: str, state: str, url: str) -> list[SGO]:
    """
    Find the first <table> on the page and extract one SGO per row.

    Reads the header row (th or first tr) to locate name, EIN, address,
    phone, email, and website columns when present.
    Falls back to first-column-only for tables without recognised headers.
    """
    if len(html.encode()) > MAX_BYTES:
        raise ValueError(f"HTML from {url} exceeds size limit")

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return parse_html_list(html, state, url)

    HEADER_WORDS = {"name", "organization", "sgo", "scholarship", "no.", "#", "entity", "document"}
    all_rows = table.find_all("tr")

    # Detect header row and build column index map
    col: dict[str, int | None] = {f: None for f in _HTML_COL_ALIASES}
    data_rows = all_rows
    if all_rows:
        header_cells = [td.get_text(separator=" ", strip=True) for td in all_rows[0].find_all(["td", "th"])]
        first_word = header_cells[0].lower().split()[0] if header_cells and header_cells[0].split() else ""
        if first_word in HEADER_WORDS:
            for field, aliases in _HTML_COL_ALIASES.items():
                col[field] = _col_index(header_cells, aliases)
            data_rows = all_rows[1:]

    def _cell(cells: list[str], field: str) -> str | None:
        idx = col.get(field)
        if idx is not None and idx < len(cells):
            v = cells[idx].strip()
            return v or None
        return None

    results = []
    for row in data_rows:
        cells = [td.get_text(separator=" ", strip=True) for td in row.find_all(["td", "th"])]
        if not cells:
            continue
        name = _cell(cells, "name") or cells[0]
        first_word = name.lower().split()[0] if name.split() else ""
        if first_word in HEADER_WORDS:
            continue
        # Strip trailing file-size annotations like "(PDF, 941.96 KB)"
        name = re.sub(r"\s*\((?:PDF|XLSX?|DOC|CSV)[^)]*\)\s*$", "", name, flags=re.IGNORECASE).strip()
        if not name:
            continue
        try:
            results.append(SGO(
                state=state,
                name=name,
                ein=_cell(cells, "ein"),
                raw_source=url,
                address=_cell(cells, "address"),
                phone=_cell(cells, "phone"),
                email=_cell(cells, "email"),
                website=_cell(cells, "website"),
            ))
        except ValueError:
            pass

    if not results:
        raise ValueError(f"No SGO names extracted from HTML table: {url}")

    return results


def parse_html_list(html: str, state: str, url: str) -> list[SGO]:
    """
    Extract SGO names from <li> or <a> elements when there is no table.

    Restricts to main content area (strips nav/header/footer first).
    Deduplicates names while preserving order.
    """
    if len(html.encode()) > MAX_BYTES:
        raise ValueError(f"HTML from {url} exceeds size limit")

    soup = BeautifulSoup(html, "html.parser")

    # Remove navigation chrome so we only see content items
    for chrome in soup.find_all(["nav", "header", "footer"]):
        chrome.decompose()

    # Prefer a semantic content container; fall back to body
    root = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find("div", class_=lambda c: c and any(w in c for w in ("content", "entry", "main")))
        or soup.body
        or soup
    )

    results = []
    seen: set[str] = set()

    # Prefer <li> items inside classed <ul>/<ol> (styled content lists, not bare nav);
    # fall back to all <li>, then plain <a> links
    classed_lists = root.find_all(["ul", "ol"], class_=True)  # type: ignore[union-attr]
    if classed_lists:
        candidates = [li for lst in classed_lists for li in lst.find_all("li", recursive=False)]
    else:
        candidates = root.find_all("li") or root.find_all("a")  # type: ignore[union-attr]

    for tag in candidates:
        text = tag.get_text(separator=" ", strip=True)
        if text in seen:
            continue
        seen.add(text)
        try:
            results.append(SGO(state=state, name=text, ein=None, raw_source=url))
        except ValueError:
            pass

    if not results:
        raise ValueError(f"No SGO names extracted from HTML list: {url}")

    return results
