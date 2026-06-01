"""
HTTP headers and URL registry for the SGO pipeline.

`urls`         — all source URLs keyed by a descriptive name that encodes the
                 state (first 2 chars) and format ("pdf", "xlsx", "csv", "word",
                 "page list", "page source").
`blocked_urls` — entries known to be blocked as of the last check; skipped by
                 run() and check_urls() so they don't slow down every run.
`HEADERS`      — browser-like request headers sent with every HTTP request.
"""

# Full Chrome 124 header set.  Many government WAFs and Cloudflare-backed sites
# fingerprint requests by checking for the Sec-Fetch-* and sec-ch-ua client-hint
# headers that standard scrapers omit.  Sending the complete set makes our
# requests indistinguishable from a real browser navigation.
HEADERS: dict[str, str] = {
    # ── identity ──────────────────────────────────────────────────────────────
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    # Client-hint brand list — must match the UA string above
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',

    # ── content negotiation ───────────────────────────────────────────────────
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",

    # ── fetch metadata (filled in by Chrome on every top-level navigation) ────
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",       # direct address-bar navigation
    "Sec-Fetch-User": "?1",         # user-initiated

    # ── connection ────────────────────────────────────────────────────────────
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Cache-Control": "max-age=0",
}

urls: dict[str, str] = {
    # Keys containing "page source" are navigation/program pages used only by
    # link_checker.py to discover current download URLs.  run() silently skips them.
    "AL page list":            "https://www.revenue.alabama.gov/legal/annual-public-report-information/",
    "AZ page source":          "https://azdor.gov/tax-credits/certification-school-tuition-organizations",
    "AZ pdf list":             "https://azdor.gov/sites/default/files/2023-06/REPORTS_sto-i-list.pdf",
    "FL page list":            "https://www.fldoe.org/schools/school-choice/k-12-scholarship-programs/sfo/",
    "GA page list":            "https://dor.georgia.gov/student-scholarship-organization-audit-reports",
    "IN page source":          "https://www.in.gov/doe/students/indiana-choice-scholarship-program/school-scholarships/",
    "IN pdf list":             "https://www.in.gov/doe/files/Certified-SGOs.pdf",
    "KS page source":          "https://www.ksde.gov/search-results?indexCatalogue=whole-site&searchQuery=SGO",
    "KS pdf list 05-2026":     "https://www.ksde.gov/docs/default-source/sf/sgo-directory-05122026.pdf",
    "LA page list":            "https://doe.louisiana.gov/topic-pages/louisiana-school-choice/tuition-donation-credit-program",
    "MO page source":          "https://www.treasurer.mo.gov/Content/MOScholars_Information/MOScholarsEAOList",
    "MO xlsx list":            "https://treasurer.mo.gov/Content/MOScholars_Information/MOScholarsEAOList2024-2025.xlsx",
    "MT page list":            "https://svc.mt.gov/dor/educationdonation2/Pages/Reports/PublicStats?dt=SSO",
    # NE: page body says "Coming soon." — no data yet; re-enable when populated
    # "NE page list":          "https://revenue.nebraska.gov/businesses/opportunity-scholarship-act/certified-scholarship-granting-organization-lists",
    "NV page source":          "https://doe.nv.gov/offices/office-of-student-and-school-supports/private-schools/nevada-educational-choice-scholarship-program-opportunity-scholarship",
    "NV pdf list":             "https://webapp-strapi-paas-prod-nde-001.azurewebsites.net/uploads/Registered_Scholarship_Organizations_af21ccf71e.pdf",
    "NH page source":          "https://www.revenue.nh.gov/taxes-glance/tax-credit-programs/nh-education-tax-credit-program",
    "NH pdf list":             "https://www.revenue.nh.gov/sites/g/files/ehbemt736/files/documents/scholarship-organizations-approved-2025-2026.pdf",
    "OH page list":            "https://charitable.ohioago.gov/Scholarship-Granting-Organization-Certification/List",
    "PA page source":          "https://dced.pa.gov/scholarship-organizations/",
    "PA download Excel list":  "https://dced.pa.gov/wp-content/themes/business2015/csv/eitc_so_list.csv",
    "RI page source":          "https://tax.ri.gov/tax-sections/credits/scholarship-credit",
    "RI pdf list":             "https://tax.ri.gov/sites/g/files/xkgbur541/files/2025-07/Tax%20Credits%20for%20Contributions%20to%20Scholarship%20Organizations%20June%2030%20SGO%20List%20for%202025.pdf",
    # SC: ECENC program is administered by a single org; no multi-org list page
    # "SC page list": "https://dor.sc.gov/tax-credits/ecenc-program-credits",
    "SD page source":          "https://dlr.sd.gov/insurance/tax_credit_program.aspx",
    "SD pdf list":             "https://dlr.sd.gov/insurance/tax_credit_program/documents/sgo_participation_list.pdf",
    "VA page source":          "https://www.doe.virginia.gov/data-policy-funding/school-finance/education-improvement-scholarships-tax-credits-program",
    "VA download Word list":   "https://www.doe.virginia.gov/home/showpublisheddocument/76022/639071974827670000",
}

# URLs confirmed blocked as of 5/28/2026 — skipped by run() to avoid slow timeouts.
# Re-check periodically with link_checker.py or check_urls().
blocked_urls: dict[str, str] = {
    "FL page list":           "403 Forbidden",
    "NH page source":         "403 Forbidden",
    # NH pdf list unblocked as of 5/2026 after full browser-header set was added
    "VA page source":         "403 Forbidden",
    "VA download Word list":  "403 Forbidden",
}

# For blocked sources that have a data list worth capturing, a human can download
# the page manually in a browser and place it here.  run() will read these files
# instead of attempting a network request.
#
# Keys must exactly match an entry in both `urls` and `blocked_urls`.
# Paths are relative to the state_lists/ directory.
# See manual/README.md for download instructions.
manual_sources: dict[str, str] = {
    "FL page list":          "manual/FL_page_list.html",
    "VA download Word list": "manual/VA_word_list.docx",
}
