"""Load a pipe-delimited ePostcard file and provide EIN -> website lookups.

Before use, set _EPOSTCARD_FILEPATH to the path of data-download-epostcard.txt.

Functions
- load_ein_website_map(): loads and returns a dict mapping normalized EIN -> website
- get_website_by_ein(ein): returns website for given EIN (loads file on first call)

Normalization: EINs are normalized to 9-digit zero-padded digit-strings.
"""
from typing import Dict, Optional
import re

_ein_map: Optional[Dict[str, Optional[str]]] = None
_name_map: Optional[Dict[str, Optional[str]]] = None
_loaded_filepath: Optional[str] = None
_EPOSTCARD_FILEPATH: str = "./data/raw/data_download_epostcard.txt"

def _normalize_ein(ein: str) -> str:
    if ein is None:
        return ""
    s = str(ein)
    digits = re.sub(r"\D", "", s)
    return digits.zfill(9)


def _normalize_name(name: str) -> str:
    if name is None:
        return ""
    s = str(name).strip().lower()
    # Remove punctuation, collapse whitespace
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def load_ein_website_map() -> Dict[str, Optional[str]]:
    """Load the pipe-delimited file and return a dict mapping normalized EIN -> website.

    Uses _EPOSTCARD_FILEPATH. The file is expected to be ASCII, pipe-delimited, no header.
    Columns used: 0 = EIN, 2 = Organization Name, 7 = Website
    """
    global _ein_map, _name_map, _loaded_filepath
    if not _EPOSTCARD_FILEPATH:
        raise ValueError("_EPOSTCARD_FILEPATH not set. Set it to the path of data-download-epostcard.txt")
    if _ein_map is not None and _loaded_filepath == _EPOSTCARD_FILEPATH:
        return _ein_map

    ein_map: Dict[str, Optional[str]] = {}
    name_map: Dict[str, Optional[str]] = {}

    try:
        # Primary path: use pandas for efficiency. usecols=[0,2,7] loads only
        # the needed columns from the large pipe-delimited file, avoiding
        # unnecessary I/O and memory overhead.
        import pandas as pd

        df = pd.read_csv(
            _EPOSTCARD_FILEPATH,
            sep="|",
            header=None,
            usecols=[0, 2, 7],
            dtype=str,
            engine="python",
            names=["EIN", "OrgName", "Website"],
            encoding="ascii",
            on_bad_lines="skip",
        )

        for _, row in df.iterrows():
            ein_raw = row["EIN"]
            org_name = row["OrgName"]
            website = row["Website"]
            if pd.isna(ein_raw):
                continue
            norm = _normalize_ein(ein_raw)
            site = None
            if website is None or (isinstance(website, float) and pd.isna(website)):
                site = None
            else:
                site = str(website).strip()
            ein_map[norm] = site
            # Populate name map if org name present; keep first encountered non-empty site
            if org_name is not None and not pd.isna(org_name):
                nname = _normalize_name(org_name)
                if nname and nname not in name_map:
                    name_map[nname] = site

    except Exception:
        # Fallback: if pandas is unavailable or fails, use the standard CSV module.
        # Less efficient (reads all columns before extracting the three needed),
        # but ensures robustness if pandas import/execution fails.
        import csv
        import sys

        try:
            # Allow very large fields in the fallback CSV reader.
            csv.field_size_limit(sys.maxsize)
        except OverflowError:
            csv.field_size_limit(2**31 - 1)

        with open(_EPOSTCARD_FILEPATH, "r", encoding="ascii", errors="replace") as fh:
            reader = csv.reader(fh, delimiter="|")
            for row in reader:
                    if len(row) <= 7:
                        continue
                    ein_raw = row[0]
                    org_name = row[2] if len(row) > 2 else None
                    website = row[7]
                    if ein_raw is None or ein_raw == "":
                        continue
                    norm = _normalize_ein(ein_raw)
                    site = website.strip() if website is not None and website != "" else None
                    ein_map[norm] = site
                    if org_name:
                        nname = _normalize_name(org_name)
                        if nname and nname not in name_map:
                            name_map[nname] = site

    _ein_map = ein_map
    _name_map = name_map
    return _ein_map


def get_website_by_ein(ein: str) -> Optional[str]:
    """Return the website for `ein`.

    Loads the EIN->website map on first call. EINs will be normalized to 9-digit
    zero-padded strings before lookup. Requires _EPOSTCARD_FILEPATH to be set.
    """
    global _ein_map
    if _ein_map is None:
        load_ein_website_map()

    norm = _normalize_ein(ein)
    return _ein_map.get(norm)


def get_website_by_name(name: str) -> Optional[str]:
    """Return website for normalized organization `name` if present in the ePostcard data."""
    global _name_map
    if _ein_map is None or _name_map is None:
        load_ein_website_map()

    if name is None:
        return None
    nname = _normalize_name(name)
    return _name_map.get(nname)


def get_website_with_status(ein: str = None, name: str = None) -> str:
    """Return a website link or a status string.

    Returns a website link, if found, or None if website field is blank, or no matching EIN or name in the 990N data

    Priority: EIN lookup takes precedence. If an EIN is present in the
    990N data (even if its website is blank) we return that result and do
    not fallback to name.
    """
    global _ein_map, _name_map
    if _ein_map is None or _name_map is None:
        load_ein_website_map()

    # Normalize inputs
    ein_input = None if ein is None or str(ein).strip() == "" else _normalize_ein(ein)
    name_input = None if name is None or str(name).strip() == "" else _normalize_name(name)

    # EIN has priority
    if ein_input:
        if ein_input in _ein_map:
            site = _ein_map.get(ein_input)
            return site if site else None
        # EIN not in map -> fall through to name lookup

    if name_input:
        if name_input in _name_map:
            site = _name_map.get(name_input)
            return site if site else None

    return None


def get_website(ein: str = None, name: str = None) -> Optional[str]:
    """Compatibility wrapper: return only the website string (or None)."""
    site = get_website_with_status(ein=ein, name=name)

    # Check for bad values - "N/A", "None", etc.
    if (site.casefold() == "N/A".casefold()) or (site.casefold() == "N\\A".casefold()) or (site.casefold() == "none".casefold()):
        site = None

    return site
