# state_lists

Downloads and parses the SGO (Scholarship Granting Organization) lists published
by each participating state, then writes a combined CSV and Excel file.

---

## Usage

**Run the full pipeline:**
```
py lists_main.py
```
Outputs `sgo_lists.csv` and `sgo_lists.xlsx` in this folder.

**Check for updated download links:**
```
py link_checker.py
```
Scrapes each state's source page to see if any annual file URLs have changed.
Prompts before applying updates to `lists_main.py`.

---

## Files

| File | Purpose |
|------|---------|
| `lists_main.py` | Main script. Holds the `urls` dict, fetches each source, dispatches to the right parser, post-processes results, and writes output. |
| `link_checker.py` | Maintenance script. Detects stale download URLs by scraping state source pages and offers to update `lists_main.py` in place. |
| `models.py` | Defines the `SGO` dataclass — the shared output schema for all parsers. |
| `sgo_lists.csv` | Output: one row per organization, all states combined. |
| `sgo_lists.xlsx` | Same data as the CSV, columns auto-fitted. |

### parsers/

| File | Handles |
|------|---------|
| `html_parser.py` | HTML pages — tries table extraction first, falls back to list/link extraction. |
| `pdf_parser.py` | PDF files — tries embedded table extraction first, falls back to line-by-line text. |
| `file_parser.py` | Excel (`.xlsx`), CSV, and Word (`.docx`) files. |
| `state_parsers.py` | State-specific PDF parsers for AZ, KS, and NV, whose PDFs pack all fields into single concatenated strings that the generic parser can't split. |

---

## Output columns

`state`, `name`, `ein`, `address`, `phone`, `email`, `website`, `raw_source`

Not every state provides every field. EIN is currently populated for OH only,
which includes it in its published HTML table.

---

## Adding a new state

1. Add an entry to the `urls` dict in `lists_main.py`. The key name controls which
   parser is used: include `"pdf"`, `"xlsx"`, `"csv"`, `"word"`, or `"page list"` in
   the key, e.g. `"TX pdf list"`.
2. If the state's source page links to an annual file, add it to `LINK_HINTS` in
   `link_checker.py` so future URL changes are caught automatically.
3. If the file format doesn't parse cleanly with the generic parsers, add a
   state-specific function in `parsers/state_parsers.py` and register it in the
   `_STATE_PDF_PARSERS` dict in `lists_main.py`.

---

## States covered

| State | Source type | Contact data |
|-------|-------------|--------------|
| AL | HTML list | name only |
| AZ | PDF (custom parser) | name, address, phone, website |
| GA | HTML list | name only |
| IN | PDF | name only |
| KS | PDF (custom parser) | name, address, phone, email |
| MO | Excel (.xlsx) | name only |
| MT | HTML table | name only |
| NV | PDF (custom parser) | name, address, phone, email |
| NH | PDF | name only |
| OH | HTML table | name, ein, address | ← only state with EIN |
| PA | CSV download | name, address, phone, email, website |
| RI | PDF | name only |
| SD | PDF | name only |
| VA | Word (.docx) *(blocked as of 5/2026)* | name only |
