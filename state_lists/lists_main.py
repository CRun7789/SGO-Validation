import csv
import re
import sys
import requests
import time

sys.stdout.reconfigure(encoding="utf-8")
from dataclasses import dataclass, asdict
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Parsers (import here so missing deps surface immediately at startup)
# ---------------------------------------------------------------------------
sys.path.insert(0, __file__.replace("lists_main.py", ""))  # ensure local imports work
from models import SGO
from parsers.html_parser import parse_html_table, parse_html_list
from parsers.pdf_parser import parse_pdf
from parsers.file_parser import parse_xlsx, parse_csv, parse_docx
from parsers.state_parsers import parse_pdf_az, parse_pdf_ks, parse_pdf_nv

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xhtml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

@dataclass
class Result:
    url: str
    status: int | None
    blocked: bool | None
    reason: str

def check_site(url: str, session: requests.Session) -> Result:
    try:
        r = session.get(url, headers=HEADERS, timeout=10, allow_redirects=True, verify=False) # don't verify SSL for now
        html = r.text.lower()

        # Detect soft blocks (200 OK but actually a challenge page)
        block_signals = [
            "just a moment", "access denied", "bot detected",
            "are you human", "checking your browser", "ddos-guard",
        ]
        soft_blocked = any(sig in html for sig in block_signals)

        if r.status_code == 403:
            return Result(url, r.status_code, True, "403 Forbidden")
        elif r.status_code == 429:
            return Result(url, r.status_code, True, "Rate limited")
        elif soft_blocked:
            return Result(url, r.status_code, True, "Soft block / challenge page")
        else:
            return Result(url, r.status_code, False, "OK")

    except requests.exceptions.SSLError:
        return Result(url, None, True, "SSL error")
    except requests.exceptions.ConnectionError:
        return Result(url, None, None, "Connection failed (down or unreachable)")
    except requests.exceptions.Timeout:
        return Result(url, None, None, "Timeout")

urls = {
    "AL page list": "https://www.revenue.alabama.gov/legal/annual-public-report-information/",
    "AZ page source": "https://azdor.gov/tax-credits/certification-school-tuition-organizations",
    "AZ pdf list": "https://azdor.gov/sites/default/files/2023-06/REPORTS_sto-i-list.pdf",
    "FL page list": "https://www.fldoe.org/schools/school-choice/k-12-scholarship-programs/sfo/",
    "GA page list": "https://dor.georgia.gov/student-scholarship-organization-audit-reports",
    "IN page source": "https://www.in.gov/doe/students/indiana-choice-scholarship-program/school-scholarships/",
    "IN pdf list": "https://www.in.gov/doe/files/Certified-SGOs.pdf",
    "KS page source": "https://www.ksde.gov/search-results?indexCatalogue=whole-site&searchQuery=SGO",
    "KS pdf list 05-2026": "https://www.ksde.gov/docs/default-source/sf/sgo-directory-05122026.pdf",
    # LA: program page only links to annual reports (school performance data), no machine-readable STO list available yet
    # "LA page list": "https://doe.louisiana.gov/topic-pages/louisiana-school-choice/tuition-donation-credit-program",
    "MO page source": "https://www.treasurer.mo.gov/Content/MOScholars_Information/MOScholarsEAOList",
    "MO xlsx list": "https://treasurer.mo.gov/Content/MOScholars_Information/MOScholarsEAOList2024-2025.xlsx",
    "MT page list": "https://svc.mt.gov/dor/educationdonation2/Pages/Reports/PublicStats?dt=SSO",
    "NV page source": "https://doe.nv.gov/offices/office-of-student-and-school-supports/private-schools/nevada-educational-choice-scholarship-program-opportunity-scholarship",
    "NV pdf list": "https://webapp-strapi-paas-prod-nde-001.azurewebsites.net/uploads/Registered_Scholarship_Organizations_af21ccf71e.pdf",
    "NH page source": "https://www.revenue.nh.gov/taxes-glance/tax-credit-programs/nh-education-tax-credit-program",
    "NH pdf list": "https://www.revenue.nh.gov/sites/g/files/ehbemt736/files/documents/scholarship-organizations-approved-2025-2026.pdf",
    "OH page list": "https://charitable.ohioago.gov/Scholarship-Granting-Organization-Certification/List",
    "PA page list": "https://dced.pa.gov/scholarship-organizations/",
    "PA download Excel list": "https://dced.pa.gov/wp-content/themes/business2015/csv/eitc_so_list.csv",
    "RI page source": "https://tax.ri.gov/tax-sections/credits/scholarship-credit",
    "RI pdf list": "https://tax.ri.gov/sites/g/files/xkgbur541/files/2025-07/Tax%20Credits%20for%20Contributions%20to%20Scholarship%20Organizations%20June%2030%20SGO%20List%20for%202025.pdf",
    # SC: ECENC program administered by single org (Exceptional SC); no list page with multiple SGOs
    # "SC page list": "https://dor.sc.gov/tax-credits/ecenc-program-credits",
    "SD page source": "https://dlr.sd.gov/insurance/tax_credit_program.aspx",
    "SD pdf list": "https://dlr.sd.gov/insurance/tax_credit_program/documents/sgo_participation_list.pdf",
    "VA page source": "https://www.doe.virginia.gov/data-policy-funding/school-finance/education-improvement-scholarships-tax-credits-program",
    "VA download Word list": "https://www.doe.virginia.gov/home/showpublisheddocument/76022/639071974827670000",   
}

blocked_urls = { # As of 5/28 3pm
    "FL page list": "403 Forbidden",
    "NH page source": "403 Forbidden",
    "NH pdf list": "403 Forbidden",
    "VA page source": "403 Forbidden",
    "VA download Word list": "403 Forbidden"
}

session = requests.Session()  # reuse TCP connections, stores cookies

def fetch_bytes(url: str, session: requests.Session) -> bytes:
    """Download raw bytes from url. Raises requests.HTTPError on non-2xx."""
    r = session.get(url, headers=HEADERS, timeout=15, allow_redirects=True, verify=False)
    r.raise_for_status()
    return r.content

_STATE_PDF_PARSERS = {
    "az": parse_pdf_az,
    "ks": parse_pdf_ks,
    "nv": parse_pdf_nv,
}


def get_parser(name: str):
    """
    Return the appropriate parser based on the key name from the urls dict.
    Key names already encode the type ("pdf list", "xlsx list", etc.).
    State-specific PDF parsers override the generic one for AZ, KS, and NV.
    """
    n = name.lower()
    if "pdf" in n:
        state_code = name[:2].lower()
        state_parser = _STATE_PDF_PARSERS.get(state_code)
        if state_parser:
            return lambda content, state, url: state_parser(content, state, url)
        return lambda content, state, url: parse_pdf(content, state, url)
    if "xlsx" in n:
        return lambda content, state, url: parse_xlsx(content, state, url)
    if "csv" in n or "excel" in n:
        return lambda content, state, url: parse_csv(content, state, url)
    if "word" in n:
        return lambda content, state, url: parse_docx(content, state, url)
    # HTML sources: "page list" uses table extraction, "page source" uses list extraction
    if "page list" in n:
        return lambda content, state, url: parse_html_table(content.decode("utf-8", errors="replace"), state, url)
    return lambda content, state, url: parse_html_list(content.decode("utf-8", errors="replace"), state, url)


_CID_MAP = {
    "(cid:415)": "ti",  # 'ti' ligature in certain PDF fonts
}

_TEXT_FIXES = {
    "â€™": "'",  # UTF-8 right single quotation mark mis-decoded as Windows-1252
}

_NON_SGO_STARTS = (
    "pursuant to", "the following scholarship", "these qualified",
    "received cash donations", "scholarship organizations which",
    "scholarship organizations under",
    "organizations under", "organizations which",
    "authorized under this chapter",
    "for the 20",                               # "for the 2025 calendar year."
    "note:", "registered scholarship grant",
    "organizations (sgos)", "sto name", "sgo name",
    "school tuition organizations certified",
    "scholarship granting organizations certified",
    "scholarship organization name",            # column header "Scholarship Organization Name"
    "name address", "address city", "mailing address",
    "add me to your", "get on ",
)

# Job-title pattern: "Firstname Lastname, Title [more words]"
_CONTACT_TITLE_RE = re.compile(
    r"^[\w\-']+ [\w\-']+,\s+[\w\s]*(CEO|President|Director|Manager|Coordinator|Founder|Administrator|Principal|Officer|Chair|Treasurer|Secretary|Staff)\b",
    re.IGNORECASE,
)

# Trailing phone number on an otherwise-valid name line, e.g. "Org Name (888)707-2465"
# Also catches vanity numbers like "(866)622-4ASK"
_TRAILING_PHONE_RE = re.compile(
    r"\s*\(?\d{3}\)?[\s.-]?[\d]{3}[\s.-][\d\w]{4}(\s*\(fax\))?$",
    re.IGNORECASE,
)

# Trailing website or address junk after an org name, e.g. " www.org.org PO Box"
_TRAILING_URL_RE = re.compile(r"\s+(?:www\.|https?://)\S+.*$", re.IGNORECASE)
_TRAILING_PO_RE = re.compile(r"\s+P\.?O\.?\s+Box.*$", re.IGNORECASE)

# Trailing bracket status annotation, e.g. "[no contributions received]"
_TRAILING_BRACKET_RE = re.compile(r"\s*\[.+\]$")

_NON_SGO_PATTERNS = [
    re.compile(r, re.IGNORECASE) for r in [
        r"^\(?\d{4}[-–]\d{4}\)?$",                         # year range: 2025-2026
        r"^\(updated .+\)$",                                # (updated April, 2026)
        r"^\(?\d{3}\)?[\s.-]?\d{3}[\s.-]\d{4}$",           # bare phone number
        r"^[\w.+\-]+@[\w\-]+\.[a-z]{2,}$",                 # bare email address
        r"^https?://",                                      # bare URL
        r"^www\.",                                          # bare URL
        # Street address: starts with a number + optional direction + any words + a street type
        r"^\d{1,6}[,.\s]+(W\.?|E\.?|N\.?|S\.?|West|East|North|South)?\s*.{0,60}\b(Street|St\b|Ave\b|Avenue|Blvd|Boulevard|Rd\b|Road|Dr\b|Drive|Way\b|Lane\b|Ln\b|Pkwy|Parkway|Circle|Ct\b|Court|Suite|Ste\b)\b",
        # Line with embedded email (contact-person lines like "Name, Title email@org")
        r"\S+@\S+\.\w{2,}",
        # Line ending with "(fax)" — always a contact line
        r"\(fax\)$",
        # "City, ST 12345" pattern (city/state/zip line)
        r"\b[A-Z]{2}\s+\d{5}\b",
        # Website embedded in what looks like contact info: ends with ".org" or ".com" alone
        r"\b\w+\.(org|com|net|edu)\s*$",
    ]
]


def _fix_cids(text: str) -> str:
    for cid, replacement in _CID_MAP.items():
        text = text.replace(cid, replacement)
    for bad, good in _TEXT_FIXES.items():
        text = text.replace(bad, good)
    return text


def _is_sgo(name: str) -> bool:
    """Return True if the name looks like an actual org, not a header/footer/contact line."""
    t = name.strip()
    if len(t) < 4:
        return False
    tl = t.lower()
    if any(tl.startswith(p) for p in _NON_SGO_STARTS):
        return False
    if _CONTACT_TITLE_RE.match(t):
        return False
    if any(pat.search(t) for pat in _NON_SGO_PATTERNS):
        return False
    return True


def postprocess(sgos: list[SGO]) -> list[SGO]:
    """
    Clean the extracted SGO list before writing:
      1. Replace known PDF encoding artifacts (e.g. (cid:415) → t).
      2. Remove entries that are obviously not org names (headers, addresses,
         phone/email lines, legislative preamble, date strings, etc.).
      3. Deduplicate within each state (same name + same state = one record).
    """
    cleaned: list[SGO] = []
    seen: set[tuple[str, str]] = set()

    removed = 0
    for sgo in sgos:
        name = _fix_cids(sgo.name)
        # Filter original before stripping — catches lines whose full content is contact info
        if not _is_sgo(name):
            removed += 1
            continue
        # Convert ALL CAPS names to Title Case, but only if the name has spaces
        # (single-word/hyphenated acronyms like CISE-SGO are left alone)
        if name.isupper() and " " in name:
            name = name.title()
        # Strip trailing status annotations, phones, URLs, and address junk
        name = _TRAILING_BRACKET_RE.sub("", name).strip()
        name = _TRAILING_PHONE_RE.sub("", name).strip()
        name = _TRAILING_URL_RE.sub("", name).strip()
        name = _TRAILING_PO_RE.sub("", name).strip()
        if not _is_sgo(name):
            removed += 1
            continue
        key = (sgo.state, name.lower())
        if key in seen:
            continue
        seen.add(key)
        sgo.name = name
        cleaned.append(sgo)

    print(f"\nPost-processing: removed {removed} non-SGO entries, {len(sgos) - removed - len(cleaned)} duplicates → {len(cleaned)} records remain")
    return cleaned


def write_results(sgos: list[SGO], path: str) -> None:
    """Write extracted SGO records to a CSV file."""
    fieldnames = ["state", "name", "ein", "address", "phone", "email", "website", "raw_source"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(s) for s in sgos)
    print(f"Wrote {len(sgos)} SGO records to {path}")

    xlsx_path = path.replace(".csv", ".xlsx")
    export_xlsx(sgos, fieldnames, xlsx_path)


def export_xlsx(sgos: list[SGO], fieldnames: list[str], path: str) -> None:
    """Write SGO records to an Excel file with columns auto-fitted to their content."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active

    ws.append(fieldnames)

    col_widths = [len(h) for h in fieldnames]
    for sgo in sgos:
        row = [getattr(sgo, f) or "" for f in fieldnames]
        ws.append(row)
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    for i, width in enumerate(col_widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width + 2

    wb.save(path)
    print(f"Wrote {len(sgos)} SGO records to {path}")


def check_urls():
    print(f"\nThis function will check {len(urls)} URLs to see if they can be accessed by Python.\n")

    for name, url in urls.items():
        print(f"-----------\nChecking {name} - {url}")
        result = check_site(url, session)
        status = f"[{result.status}]" if result.status else "[---]"
        flag = "🚫 BLOCKED" if result.blocked else ("✅ OK" if result.blocked is False else "⚠️  UNKNOWN")
        print(f"{flag} {status} {result.url}  —  {result.reason}")
        time.sleep(1)  # be polite; also reduces rate-limit triggers


def run(output_path: str = "sgo_lists.csv") -> None:
    """
    Fetch and parse every accessible data source; write results to output_path.

    Skips:
    - URLs in blocked_urls (known-blocked as of last check)
    - "page source" keys (navigation/program pages, not data sources)
    """
    all_sgos: list[SGO] = []

    for name, url in urls.items():
        if name in blocked_urls:
            print(f"[SKIP] {name} — blocked ({blocked_urls[name]})")
            continue
        if "page source" in name.lower():
            print(f"[SKIP] {name} — navigation page, no direct list")
            continue

        state = name[:2].upper()
        parser = get_parser(name)

        print(f"\n[{state}] Fetching {name} ...")
        try:
            content = fetch_bytes(url, session)
            sgos = parser(content, state, url)
            print(f"  → {len(sgos)} SGOs extracted")
            all_sgos.extend(sgos)
        except Exception as e:
            print(f"  FAILED: {e}")

        time.sleep(1)  # be polite

    all_sgos = postprocess(all_sgos)
    write_results(all_sgos, output_path)


if __name__ == "__main__":
    run()