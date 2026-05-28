"""
Extract SGO names from PDF files using pdfplumber.

pdfplumber handles table extraction better than PyPDF2 for the
government PDFs in this project (many are scanned or have embedded tables).
Install: pip install pdfplumber
"""
import io
from models import SGO

try:
    import pdfplumber
except ImportError as e:
    raise ImportError("pdfplumber is required: pip install pdfplumber") from e

MAX_BYTES = 50_000_000  # 50 MB guard against malformed/malicious files


def parse_pdf(pdf_bytes: bytes, state: str, url: str) -> list[SGO]:
    """
    Extract SGO names from a PDF.

    Tries table extraction first (for PDFs with embedded tables).
    Falls back to plain text extraction line-by-line if no tables found.
    Returns a list of SGO objects; raises ValueError if nothing was extracted.
    """
    if len(pdf_bytes) > MAX_BYTES:
        raise ValueError(f"PDF from {url} exceeds {MAX_BYTES // 1_000_000} MB size limit")

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
    HEADER_WORDS = {"name", "organization", "sgo", "scholarship", "entity", "no.", "#"}
    results = []

    for row in table:
        if not row:
            continue
        # Take the first non-empty cell as the candidate name
        candidate = next((cell for cell in row if cell and cell.strip()), None)
        if not candidate:
            continue
        cleaned = candidate.strip()
        if cleaned.lower() in HEADER_WORDS or cleaned.lower().startswith("name"):
            continue
        try:
            results.append(SGO(state=state, name=cleaned, ein=None, raw_source=url))
        except ValueError:
            pass  # empty or too-long names are skipped

    return results


def _sgos_from_text(text: str, state: str, url: str) -> list[SGO]:
    """
    Fallback: treat each non-blank line as a potential org name.
    Filters out lines that are obviously page numbers, headers, or footers.
    """
    SKIP_PREFIXES = ("page ", "date ", "state of ", "department ", "updated ")
    results = []

    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.isdigit():
            continue
        if any(cleaned.lower().startswith(p) for p in SKIP_PREFIXES):
            continue
        try:
            results.append(SGO(state=state, name=cleaned, ein=None, raw_source=url))
        except ValueError:
            pass

    return results
