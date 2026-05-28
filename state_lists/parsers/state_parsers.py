"""
State-specific PDF parsers for AZ, KS, and NV.

All three PDFs pack multiple fields into single text runs that the generic
parser cannot split into columns.  Each parser uses regex to extract the
available fields from the concatenated text.

Fields extracted by state:
  AZ — name, address, phone, website  (no EIN, no email)
  KS — name, address, phone, email    (no EIN, no website)
  NV — name, address, phone, email    (no EIN; website unreliable — omitted)
"""
import io
import re
from models import SGO

try:
    import pdfplumber
except ImportError as e:
    raise ImportError("pdfplumber is required: pip install pdfplumber") from e

MAX_BYTES = 50_000_000

# ── shared patterns ──────────────────────────────────────────────────────────

_PHONE_RE    = re.compile(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-][\d\w]{4}")
_EMAIL_RE    = re.compile(r"[\w.+\-]+@[\w\-]+\.[a-z]{2,}", re.IGNORECASE)
# State abbreviation + zip (no word-boundary requirement after digits — KS glues CEO name to zip)
_STATE_ZIP_RE = re.compile(r"([A-Z]{2})\s+(\d{5})")
# First street-number token inside a string (2–6 digits surrounded by spaces)
_STREET_START_RE = re.compile(r"\s+\d{2,6}\s+")

HEADER_WORDS = {
    "name", "sto", "sgo", "mailing", "phone", "website", "dates", "address",
    "city", "state", "zip", "ceo", "contact", "email", "telephone", "certified",
    "tax", "organizations",
}


def _is_header(text: str) -> bool:
    words = text.lower().split()
    return bool(words) and words[0] in HEADER_WORDS


def _split_name_address(text: str) -> tuple[str, str | None]:
    """Return (name, street_address) by splitting at the first street number."""
    m = _STREET_START_RE.search(text)
    if not m:
        return text.strip(), None
    name = text[: m.start()].strip()
    rest = text[m.start():]
    zip_m = _STATE_ZIP_RE.search(rest)
    address = rest[: zip_m.end()].strip() if zip_m else None
    return name, address


# ── AZ ───────────────────────────────────────────────────────────────────────
#
# Each PDF table row is collapsed by pdfplumber to a single string:
#   'OrgName StreetAddr Phone Website DateRange [NameContinued] City, AZ Zip'
#
# Strategy: strip phone, website, and date-range tokens; split on the first
# street number to get name and address; rejoin the city+state+zip from the
# end of the stripped string.

_AZ_DATE_RE    = re.compile(r"\d{2}/\d{2}/\d{2,4}\s*[–—-]\s*(?:Present|Past|\d{2}/\d{2}/\d{2,4})", re.IGNORECASE)
_AZ_PHONE_RE   = re.compile(r"\d{3}-\d{3}-\d{4}")
_AZ_WEBSITE_RE = re.compile(r"\b[\w-]+\.[a-z]{2,}\b", re.IGNORECASE)


def parse_pdf_az(pdf_bytes: bytes, state: str, url: str) -> list[SGO]:
    if len(pdf_bytes) > MAX_BYTES:
        raise ValueError(f"PDF from {url} exceeds size limit")

    results: list[SGO] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    cell = next((c for c in row if c and c.strip()), None)
                    if not cell:
                        continue
                    text = " ".join(cell.split())
                    if _is_header(text):
                        continue

                    # Extract fields before stripping them from the text
                    phone_m = _AZ_PHONE_RE.search(text)
                    phone: str | None = phone_m.group() if phone_m else None

                    web_m = _AZ_WEBSITE_RE.search(text)
                    website: str | None = web_m.group() if web_m else None

                    # Remove phone, website, and date noise to isolate name+address
                    stripped = text
                    if phone_m:
                        stripped = stripped.replace(phone_m.group(), "")
                    if web_m:
                        stripped = stripped.replace(web_m.group(), "")
                    stripped = _AZ_DATE_RE.sub("", stripped)
                    stripped = " ".join(stripped.split())

                    name, address = _split_name_address(stripped)
                    if not name or _is_header(name):
                        continue

                    # If there's still a city+state+zip at the very end that wasn't
                    # captured in address (it occurs after the date-range fragment),
                    # append it to the address.
                    if address is None:
                        city_m = _STATE_ZIP_RE.search(stripped)
                        if city_m:
                            address = stripped[stripped.rfind(" ", 0, city_m.start()) + 1: city_m.end()].strip()

                    # Remove stray corporate-suffix tokens (Inc., LLC, etc.) that PDF
                    # column reflow inserts between street and city.
                    if address:
                        address = re.sub(r"\s+(?:Inc|LLC|Ltd|Corp|LLP)\.?\s+", " ", address).strip()

                    try:
                        results.append(SGO(
                            state=state, name=name, ein=None, raw_source=url,
                            address=address or None,
                            phone=phone,
                            email=None,
                            website=website,
                        ))
                    except ValueError:
                        pass

    if not results:
        raise ValueError(f"No SGO names extracted from AZ PDF: {url}")

    return results


# ── KS ───────────────────────────────────────────────────────────────────────
#
# Each PDF row is a single string:
#   'OrgName StreetAddr City ST ZipCEOName ContactName Phone Email'
#
# The zip is glued directly to the CEO first name (no space), so we cannot
# rely on a word boundary after the 5-digit zip.

def parse_pdf_ks(pdf_bytes: bytes, state: str, url: str) -> list[SGO]:
    if len(pdf_bytes) > MAX_BYTES:
        raise ValueError(f"PDF from {url} exceeds size limit")

    results: list[SGO] = []

    # KS PDF needs the Referer header — use a fresh session-like call via pdfplumber
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    cell = next((c for c in row if c and c.strip()), None)
                    if not cell:
                        continue
                    text = " ".join(cell.split())
                    if _is_header(text):
                        continue

                    # Email is the last token (always at the end)
                    email: str | None = None
                    email_m = _EMAIL_RE.search(text)
                    if email_m:
                        email = email_m.group()
                        text_no_email = text[: email_m.start()].rstrip()
                    else:
                        text_no_email = text

                    # Phone: last match before the email
                    phone: str | None = None
                    phone_ms = list(_PHONE_RE.finditer(text_no_email))
                    if phone_ms:
                        phone = phone_ms[-1].group()

                    # Name: everything up to the first street number
                    street_m = _STREET_START_RE.search(text)
                    if street_m:
                        name = text[: street_m.start()].strip()
                        addr_start = street_m.start()
                        # Address: from street number through state+zip
                        # _STATE_ZIP_RE has no \b after digits, so it matches "80111Norton"
                        zip_m = _STATE_ZIP_RE.search(text, addr_start)
                        if zip_m:
                            address: str | None = text[addr_start: zip_m.end()].strip()
                        else:
                            address = None
                    else:
                        name = text_no_email.strip()
                        address = None

                    if not name or _is_header(name):
                        continue

                    try:
                        results.append(SGO(
                            state=state, name=name, ein=None, raw_source=url,
                            address=address,
                            phone=phone,
                            email=email,
                            website=None,
                        ))
                    except ValueError:
                        pass

    if not results:
        raise ValueError(f"No SGO names extracted from KS PDF: {url}")

    return results


# ── NV ───────────────────────────────────────────────────────────────────────
#
# Free-text, multi-line blocks.  Each org occupies several consecutive lines:
#   Line 1:        OrgName  (NNN)NNN-XXXX
#   Lines 2…N:     Contact Person, Title  contact@email.com   [+ fax lines]
#   Near-last:     Street address   [fax]
#   Last (maybe):  Website text
#
# Block boundary: a line that (a) has a parenthesized phone, (b) does NOT end
# with "(fax)", and (c) does NOT contain a comma (which marks "Person, Title").
# The one org without a phone on its name line (IPOF) is handled by treating
# consecutive non-address, non-contact lines as name candidates.

_NV_PHONE_PAREN_RE = re.compile(r"\(\d{3}\)\d{3}[-\s][\d\w]{4}")
_NV_FAX_RE = re.compile(r"\(fax\)\s*$", re.IGNORECASE)


def _is_nv_org_line(line: str) -> bool:
    """True if this line is an org-name line (phone present, not a fax/contact line).

    NV contact-person lines always end with an email address; org-name lines
    never do.  Using email absence is more robust than a fixed title-word list
    (which would miss titles like 'VP', 'Superintendent', 'Liaison', etc.).
    """
    return (
        bool(_NV_PHONE_PAREN_RE.search(line))
        and not _NV_FAX_RE.search(line)
        and not _EMAIL_RE.search(line)
    )


def parse_pdf_nv(pdf_bytes: bytes, state: str, url: str) -> list[SGO]:
    if len(pdf_bytes) > MAX_BYTES:
        raise ValueError(f"PDF from {url} exceeds size limit")

    all_lines: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend(ln.strip() for ln in text.splitlines() if ln.strip())

    # Split into blocks on org-name lines
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in all_lines:
        if _is_nv_org_line(line) and current:
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)

    results: list[SGO] = []
    for block in blocks:
        if not block:
            continue

        first = block[0]

        # Skip page headers / boilerplate that slipped into the first block
        if _is_header(first) or not first or len(first) < 4:
            continue

        # Phone: from the org-name line
        phone_m = _NV_PHONE_PAREN_RE.search(first)
        phone: str | None = phone_m.group() if phone_m else None
        name = first[: phone_m.start()].strip() if phone_m else first.strip()

        if not name or _is_header(name):
            continue

        # Address: first line in the block that starts with a digit
        address: str | None = None
        for line in block[1:]:
            if re.match(r"^\d", line):
                # Strip trailing fax number from the address line
                addr = re.sub(r"\s+\(?\d{3}\)?[\s.-]?\d{3}[\s.-][\d\w]{4}.*$", "", line).strip()
                # Also strip any repeated org-name text appended after city/zip
                zip_m = _STATE_ZIP_RE.search(addr)
                if zip_m:
                    addr = addr[: zip_m.end()].strip()
                address = addr or None
                break

        # Email: first email in any line after the org-name line
        email: str | None = None
        for line in block[1:]:
            em = _EMAIL_RE.search(line)
            if em:
                email = em.group()
                break

        try:
            results.append(SGO(
                state=state, name=name, ein=None, raw_source=url,
                address=address,
                phone=phone,
                email=email,
                website=None,
            ))
        except ValueError:
            pass

    if not results:
        raise ValueError(f"No SGO names extracted from NV PDF: {url}")

    return results
