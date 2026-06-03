"""
Shared constants and helpers used across multiple parser modules.

Centralising these avoids duplicating MAX_BYTES, HEADER_WORDS, _is_header,
and _col_index in html_parser, file_parser, and state_parsers.
"""

# Maximum file size accepted by any parser — guards against malformed or
# malicious downloads filling memory before we can parse them.
MAX_BYTES: int = 50_000_000  # 50 MB

# First-word tokens that identify a row as a column header rather than org data.
HEADER_WORDS: frozenset[str] = frozenset({
    "name", "sto", "sgo", "mailing", "phone", "website", "dates", "address",
    "city", "state", "zip", "ceo", "contact", "email", "telephone", "certified",
    "tax", "organizations", "organization", "scholarship", "entity",
    "no.", "#", "document", "approved", "list",
})


def is_header(text: str) -> bool:
    """Return True if *text* looks like a column header rather than an org name.

    Checks whether the first whitespace-delimited token (lowercased) is one of
    the known header words.  Used to skip header rows in tables and PDFs.
    """
    words = text.lower().split()
    return bool(words) and words[0] in HEADER_WORDS


def col_index(headers: list[str], aliases: list[str]) -> int | None:
    """Return the index of the first header that matches any alias (case-insensitive).

    Args:
        headers: The header row cells from a table or CSV.
        aliases: A list of lowercase strings to match against.

    Returns:
        The zero-based column index of the first match, or None if not found.
    """
    hl = [h.strip().lower() for h in headers]
    for alias in aliases:
        if alias in hl:
            return hl.index(alias)
    return None
