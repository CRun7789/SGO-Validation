import csv
import sys
import requests
import time
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
    blocked: bool
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
    "LA page list": "https://doe.louisiana.gov/topic-pages/louisiana-school-choice/tuition-donation-credit-program",
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
    "SC page list": "https://dor.sc.gov/tax-credits/ecenc-program-credits",
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

def get_parser(name: str):
    """
    Return the appropriate parser based on the key name from the urls dict.
    Key names already encode the type ("pdf list", "xlsx list", etc.).
    """
    n = name.lower()
    if "pdf" in n:
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


def write_results(sgos: list[SGO], path: str) -> None:
    """Write extracted SGO records to a CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["state", "name", "ein", "raw_source"])
        writer.writeheader()
        writer.writerows(asdict(s) for s in sgos)
    print(f"\nWrote {len(sgos)} SGO records to {path}")


def check_urls():
    print(f"\nThis function will check {len(urls)} URLs to see if they can be accessed by Python.\n")

    for name, url in urls.items():
        print(f"-----------\nChecking {name} - {url}")
        result = check_site(url, session)
        status = f"[{result.status}]" if result.status else "[---]"
        flag = "🚫 BLOCKED" if result.blocked else ("✅ OK" if result.blocked is False else "⚠️  UNKNOWN")
        print(f"{flag} {status} {result.url}  —  {result.reason}")
        time.sleep(1)  # be polite; also reduces rate-limit triggers

check_urls()