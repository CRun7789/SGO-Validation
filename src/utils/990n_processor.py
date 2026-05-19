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
_loaded_filepath: Optional[str] = None
_EPOSTCARD_FILEPATH: str = "./data-download-epostcard.txt"

def _normalize_ein(ein: str) -> str:
    if ein is None:
        return ""
    s = str(ein)
    digits = re.sub(r"\D", "", s)
    return digits.zfill(9)


def load_ein_website_map() -> Dict[str, Optional[str]]:
    """Load the pipe-delimited file and return a dict mapping normalized EIN -> website.

    Uses _EPOSTCARD_FILEPATH. The file is expected to be ASCII, pipe-delimited, no header.
    Columns used: 0 = EIN, 2 = Organization Name, 7 = Website
    """
    global _ein_map, _loaded_filepath
    if not _EPOSTCARD_FILEPATH:
        raise ValueError("_EPOSTCARD_FILEPATH not set. Set it to the path of data-download-epostcard.txt")
    if _ein_map is not None and _loaded_filepath == _EPOSTCARD_FILEPATH:
        return _ein_map

    ein_map: Dict[str, Optional[str]] = {}

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
            website = row["Website"]
            if pd.isna(ein_raw):
                continue
            norm = _normalize_ein(ein_raw)
            if website is None or (isinstance(website, float) and pd.isna(website)):
                ein_map[norm] = None
            else:
                ein_map[norm] = str(website).strip()

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
                website = row[7]
                if ein_raw is None or ein_raw == "":
                    continue
                norm = _normalize_ein(ein_raw)
                ein_map[norm] = website.strip() if website is not None and website != "" else None

    _ein_map = ein_map
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
