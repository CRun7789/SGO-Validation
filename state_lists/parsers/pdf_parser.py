"""
Extract SGO names from PDF files using pdfplumber.

pdfplumber handles table extraction better than PyPDF2 for the
government PDFs in this project (many are scanned or have embedded tables).
Install: pip install pdfplumber
"""
import io
import re
from models import SGO

MAX_BYTES = 50_000_000  # 50 MB guard against malformed/malicious files

_TABLE_HEADER_WORDS = {
    "name", "organization", "sgo", "scholarship", "entity",
    "no.", "#", "tax", "address", "certified", "approved", "list",
}

_TEXT_SKIP_PREFIXES = (
    "page ", "date ", "state of ", "department ", "updated ",
    "name ", "organization ", "scholarship granting", "tax credit",
)


def parse_pdf(pdf_bytes: bytes, state: str, url: str) -> list[SGO]:
    """
    Extract SGO names from a PDF.

    Tries table extraction first (for PDFs with embedded tables).
    Falls back to plain text extraction line-by-line if no tables found.
    Returns a list of SGO objects; raises ValueError if nothing was extracted.
    """
    if len(pdf_bytes) > MAX_BYTES:
        raise ValueError(f"PDF from {url} exceeds {MAX_BYTES // 1_000_000} MB size limit")

    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("pdfplumber is required: pip install pdfplumber") from e

    sgos: list[SGO] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        # Try table extraction on every page first
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                sgos.extend(_sgos_from_table(table, state, url))

        # If no table rows found, fall back to text lines
        if not sgos:
            for page in pdf.pages:
                text = page.extract_text() or ""
                sgos.extend(_sgos_from_text(text, state, url))

    if not sgos:
        raise ValueError(f"No SGO names extracted from PDF: {url}")

    return sgos


def _sgos_from_table(table: list[list[str | None]], state: str, url: str) -> list[SGO]:
    """
    Heuristic: the first column that looks like an org name column is used.
    Skips header rows (cells that match common header words).
    """
    results = []

    for row in table:
        if not row:
            continue
        # Take the first non-empty cell as the candidate name
        candidate = next((cell for cell in row if cell and cell.strip()), None)
        if not candidate:
            continue
        # Normalize internal whitespace (newlines from multi-line cells → single space)
        cleaned = " ".join(candidate.split())
        cleaned_lower = cleaned.lower()
        first_word = cleaned_lower.split()[0] if cleaned_lower.split() else ""
        if cleaned_lower in _TABLE_HEADER_WORDS or first_word in _TABLE_HEADER_WORDS:
            continue
        # If the cell bundles address+contact after the org name (e.g. KS directory PDFs),
        # extract only the text before the first street-number pattern.
        name = _extract_org_name(cleaned)
        try:
            results.append(SGO(state=state, name=name, ein=None, raw_source=url))
        except ValueError:
            pass  # empty or too-long names are skipped

    return results


def _extract_org_name(text: str) -> str:
    """
    Return just the organization name from a cell that may include an address.

    Many government directory PDFs pack the full record into one cell:
      "Org Name 123 Main St City ST 12345Contact Person 555-1234 email@example.com"
    Heuristic: the address starts with a street number, so take everything before
    the first standalone digit sequence that follows a word boundary.
    """
    # Match a street address start: whitespace + digits + whitespace (e.g. " 123 ")
    m = re.search(r"\s+\d{2,6}\s+", text)
    if m:
        return text[: m.start()].strip()
    return text


def _sgos_from_text(text: str, state: str, url: str) -> list[SGO]:
    """
    Fallback: treat each non-blank line as a potential org name.
    Filters out lines that are obviously page numbers, headers, or footers.
    """
    results = []

    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.isdigit():
            continue
        if any(cleaned.lower().startswith(p) for p in _TEXT_SKIP_PREFIXES):
            continue
        try:
            results.append(SGO(state=state, name=cleaned, ein=None, raw_source=url))
        except ValueError:
            pass

    return results
