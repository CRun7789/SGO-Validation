"""
Check whether the direct download links in lists_main.py are still current.

For each state that has a stable "source page" pointing to an annual file
(PDF, XLSX, CSV, DOCX), this script:
  1. Fetches the source page and scans its links for the current download.
  2. Compares the discovered URL to the one hardcoded in lists_main.py.
  3. If they differ, prints a diff and prompts you to apply the update.

Usage:
    py link_checker.py

States not covered (AL, FL, GA, MT, OH, PA) have either stable permanent
URLs or no separate source page; the existing check_urls() in lists_main.py
handles liveness for those.
"""
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding="utf-8")

try:
    from bs4 import BeautifulSoup
except ImportError as e:
    raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4") from e

# ---------------------------------------------------------------------------
# Reuse headers and session from lists_main
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from lists_main import HEADERS, session, urls as CURRENT_URLS

LISTS_MAIN_PATH = Path(__file__).parent / "lists_main.py"

# ---------------------------------------------------------------------------
# LINK_HINTS
#
# Maps state code → (source_page_url, href_regex)
#
# source_page_url: the stable program/info page that always links to the
#                  current download file.  Copied from the "XX page source"
#                  entries in lists_main.py — nothing new to maintain.
#
# href_regex: a pattern matched against every <a href> on that page.
#             Narrow enough to pick the right file; loose enough that a
#             year or hash in the filename can change without breaking it.
#
# Example (KS):
#   Source page has a link like:
#     .../sgo-directory-05122026.pdf   (2026 edition)
#   Next year it will be:
#     .../sgo-directory-05122027.pdf   (2027 edition)
#   The pattern  r"sgo-directory.*\.pdf"  matches both.
# ---------------------------------------------------------------------------
LINK_HINTS: dict[str, tuple[str, str]] = {
    "AZ": (
        "https://azdor.gov/tax-credits/certification-school-tuition-organizations",
        r"REPORTS_sto-i.*\.pdf",  # "i" = individual donations list (not "c" = corporate)
    ),
    "IN": (
        "https://www.in.gov/doe/students/indiana-choice-scholarship-program/school-scholarships/",
        r"[Cc]ertified.?SGOs?.*\.pdf",
    ),
    "KS": (
        "https://www.ksde.gov/search-results?indexCatalogue=whole-site&searchQuery=SGO",
        r"sgo-directory.*\.pdf",
    ),
    "MO": (
        "https://www.treasurer.mo.gov/Content/MOScholars_Information/MOScholarsEAOList",
        r"MOScholarsEAOList.*\.xlsx",
    ),
    "NV": (
        "https://doe.nv.gov/offices/office-of-student-and-school-supports/private-schools/"
        "nevada-educational-choice-scholarship-program-opportunity-scholarship",
        r"[Rr]egistered.Scholarship.*\.pdf",
    ),
    "NH": (
        "https://www.revenue.nh.gov/taxes-glance/tax-credit-programs/nh-education-tax-credit-program",
        r"scholarship-organizations.*\.pdf",
    ),
    "RI": (
        "https://tax.ri.gov/tax-sections/credits/scholarship-credit",
        r"[Ss][Gg][Oo].*[Ll]ist.*\.pdf|[Ss]cholarship.*[Oo]rganization.*[Ll]ist.*\.pdf",
    ),
    "SD": (
        "https://dlr.sd.gov/insurance/tax_credit_program.aspx",
        r"sgo.participation.*\.pdf",
    ),
    "VA": (
        "https://www.doe.virginia.gov/data-policy-funding/school-finance/"
        "education-improvement-scholarships-tax-credits-program",
        r"showpublisheddocument",
    ),
}


def find_download_link(source_url: str, pattern: str, sess: requests.Session) -> str | None:
    """
    Fetch source_url and return the first <a href> matching pattern.

    Returns an absolute URL, or None if the page is blocked or no match found.
    """
    try:
        r = sess.get(source_url, headers=HEADERS, timeout=15, allow_redirects=True, verify=False)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  [WARN] Could not fetch source page: {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    compiled = re.compile(pattern, re.IGNORECASE)
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        # Strip query strings (CMS cache-busters like ?sfvrsn=...) before matching
        href_path = href.split("?")[0]
        if compiled.search(href_path):
            absolute = urljoin(source_url, href_path)
            return absolute
    return None


def _current_download_url(state: str) -> tuple[str, str] | None:
    """
    Return (dict_key, url) for the download entry belonging to state in CURRENT_URLS.
    Looks for the key that starts with the state code and contains a file-type word.
    """
    file_types = {"pdf", "xlsx", "csv", "excel", "word", "download"}
    for key, url in CURRENT_URLS.items():
        if key[:2].upper() == state.upper() and any(ft in key.lower() for ft in file_types):
            return key, url
    return None


def _updated_key(old_key: str, old_url: str, new_url: str) -> str:
    """
    If old_key contains a 4-digit year that also appears in old_url, replace
    it with the year found in new_url.  Otherwise return old_key unchanged.

    Example:
        old_key = "KS pdf list 05-2026"
        old_url = ".../sgo-directory-05122026.pdf"   → year 2026
        new_url = ".../sgo-directory-05122027.pdf"   → year 2027
        → returns "KS pdf list 05-2027"
    """
    year_re = re.compile(r"\b(20\d{2})\b")
    key_years = year_re.findall(old_key)
    if not key_years:
        return old_key

    old_url_years = year_re.findall(old_url)
    new_url_years = year_re.findall(new_url)
    if not old_url_years or not new_url_years:
        return old_key

    # Replace only years from old_url that now appear differently in new_url
    updated = old_key
    for oy, ny in zip(old_url_years, new_url_years):
        if oy != ny and oy in key_years:
            updated = updated.replace(oy, ny, 1)
    return updated


def apply_update(old_key: str, old_url: str, new_url: str) -> None:
    """Rewrite lists_main.py, replacing old_url (and old_key if dated) in place."""
    text = LISTS_MAIN_PATH.read_text(encoding="utf-8")

    new_key = _updated_key(old_key, old_url, new_url)

    # Replace URL first, then key name (avoids double-replacement)
    if old_url not in text:
        print(f"  [ERROR] Could not find old URL in {LISTS_MAIN_PATH.name} — skipping.")
        return

    text = text.replace(old_url, new_url)
    if new_key != old_key:
        text = text.replace(f'"{old_key}"', f'"{new_key}"')

    LISTS_MAIN_PATH.write_text(text, encoding="utf-8")

    if new_key != old_key:
        print(f"  Updated key:  {old_key!r}  →  {new_key!r}")
    print(f"  Updated URL:  {old_url}\n           →  {new_url}")
    print(f"  Saved {LISTS_MAIN_PATH.name}.")


def check_all_links(urls_dict: dict[str, str]) -> None:
    """
    For each state in LINK_HINTS, discover the current download link from its
    source page and compare against the hardcoded URL.  Prompt before updating.
    """
    changed = 0
    for state, (source_url, pattern) in LINK_HINTS.items():
        entry = _current_download_url(state)
        if entry is None:
            print(f"[{state}] No download entry found in urls dict — skipping.")
            continue

        old_key, old_url = entry
        print(f"[{state}] Checking {old_key} ...", end=" ", flush=True)

        discovered = find_download_link(source_url, pattern, session)

        if discovered is None:
            print("no link found (page blocked or pattern did not match).")
            continue

        if discovered == old_url:
            print("OK, unchanged.")
            continue

        # URLs differ — show diff and prompt
        changed += 1
        print(f"\n  OLD: {old_url}\n  NEW: {discovered}")
        try:
            answer = input("  Apply this change? [y/N]: ").strip().lower()
        except EOFError:
            print("(non-interactive — skipping)")
            answer = ""
        if answer == "y":
            apply_update(old_key, old_url, discovered)
        else:
            print("  Skipped.")

    if changed == 0:
        print("\nAll checked links are up to date.")
    else:
        print(f"\n{changed} link(s) found that differ from the hardcoded URLs.")


if __name__ == "__main__":
    check_all_links(CURRENT_URLS)
