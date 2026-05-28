"""
Extract SGO names from Excel (.xlsx), CSV, and Word (.docx) files.

Install: pip install openpyxl python-docx
csv and io are stdlib — no install needed.
"""
import csv
import io
from models import SGO

try:
    import openpyxl
except ImportError as e:
    raise ImportError("openpyxl is required: pip install openpyxl") from e

try:
    import docx
except ImportError as e:
    raise ImportError("python-docx is required: pip install python-docx") from e

MAX_BYTES = 50_000_000
HEADER_WORDS = {"name", "organization", "sgo", "scholarship", "no.", "#", "entity"}


def parse_xlsx(xlsx_bytes: bytes, state: str, url: str) -> list[SGO]:
    """
    Read the first sheet of an .xlsx file and extract one SGO per row.

    Assumes the first column contains org names; skips the header row.
    """
    if len(xlsx_bytes) > MAX_BYTES:
        raise ValueError(f"xlsx from {url} exceeds size limit")

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    ws = wb.active
    results = []

    for row in ws.iter_rows(values_only=True):
        if not row:
            continue
        first = str(row[0]).strip() if row[0] is not None else ""
        if not first or first.lower() in HEADER_WORDS or first.lower().startswith("name"):
            continue
        try:
            results.append(SGO(state=state, name=first, ein=None, raw_source=url))
        except ValueError:
            pass

    wb.close()

    if not results:
        raise ValueError(f"No SGO names extracted from xlsx: {url}")

    return results


def parse_csv(csv_bytes: bytes, state: str, url: str) -> list[SGO]:
    """
    Read a CSV file and extract one SGO per row.

    Assumes the first column contains org names; skips the header row.
    """
    if len(csv_bytes) > MAX_BYTES:
        raise ValueError(f"CSV from {url} exceeds size limit")

    text = csv_bytes.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    results = []

    for i, row in enumerate(reader):
        if not row:
            continue
        first = row[0].strip()
        if i == 0 and (not first or first.lower() in HEADER_WORDS or first.lower().startswith("name")):
            continue  # skip header
        if not first:
            continue
        try:
            results.append(SGO(state=state, name=first, ein=None, raw_source=url))
        except ValueError:
            pass

    if not results:
        raise ValueError(f"No SGO names extracted from CSV: {url}")

    return results


def parse_docx(docx_bytes: bytes, state: str, url: str) -> list[SGO]:
    """
    Extract SGO names from a Word document.

    Checks tables first (one name per row), then falls back to paragraphs.
    """
    if len(docx_bytes) > MAX_BYTES:
        raise ValueError(f"docx from {url} exceeds size limit")

    doc = docx.Document(io.BytesIO(docx_bytes))
    results = []

    # Tables first
    for table in doc.tables:
        for row in table.rows:
            first = row.cells[0].text.strip() if row.cells else ""
            if not first or first.lower() in HEADER_WORDS or first.lower().startswith("name"):
                continue
            try:
                results.append(SGO(state=state, name=first, ein=None, raw_source=url))
            except ValueError:
                pass

    # Fallback: paragraphs
    if not results:
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text or text.lower() in HEADER_WORDS:
                continue
            try:
                results.append(SGO(state=state, name=text, ein=None, raw_source=url))
            except ValueError:
                pass

    if not results:
        raise ValueError(f"No SGO names extracted from docx: {url}")

    return results
