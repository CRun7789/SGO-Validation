"""
Utility functions for SGO name normalization and comparison.

normalize_name(name) -> str
    Strips articles, corporate suffixes, punctuation, and extra whitespace
    to produce a canonical key suitable for fuzzy matching or deduplication.

is_same_org(a, b) -> bool
    Returns True if two org names normalize to the same key, i.e. they
    almost certainly refer to the same organization.

Example:
    >>> is_same_org("The Children's Scholarship Fund", "Children's Scholarship Fund")
    True
    >>> is_same_org("AAA Scholarship Foundation, Inc.", "AAA Scholarship Foundation LLC")
    True
    >>> is_same_org("Step Up For Students", "Stepup for Students")
    False
"""
import re

# ── corporate / legal suffixes to strip ──────────────────────────────────────
#
# Matched at the END of the name (after punctuation is removed).
# Ordered longest-first so "llp" doesn't shadow "limited liability partnership".
# Each entry is a regex fragment; the full pattern anchors to end-of-string and
# allows an optional trailing period.

_SUFFIX_FRAGMENTS = [
    # multi-word
    r"limited liability (partnership|company|corporation)",
    r"not for profit( corporation)?",
    r"non[- ]?profit( corporation)?",
    r"public benefit corporation",
    r"professional (corporation|association)",
    # "d/b/a ..." and "dba ..." clauses — strip everything from the marker onward
    r"d/?b/?a\b.*",
    r"doing business as\b.*",
    # common single-word suffixes
    r"incorporated",
    r"corporation",
    r"foundation",  # careful: some orgs have "Foundation" as a meaningful name part;
                    # stripping it is still correct for comparison purposes
    r"association",
    r"organization",
    r"institute",
    r"society",
    r"company",
    r"limited",
    r"llp",
    r"pllc",
    r"llc",
    r"ltd",
    r"lp",
    r"inc",
    r"co",
]

# Build one compiled pattern that matches any suffix at end-of-string.
# The pattern allows optional trailing punctuation before the suffix.
_SUFFIX_RE = re.compile(
    r"\s*[,\-]?\s*\b(?:" + "|".join(_SUFFIX_FRAGMENTS) + r")\.?\s*$",
    re.IGNORECASE,
)

# ── leading articles ──────────────────────────────────────────────────────────
_LEADING_ARTICLE_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)

# ── state abbreviation tags embedded in names ─────────────────────────────────
# e.g. "AAA Scholarship Foundation- FL" or "Foundation-NV"
_STATE_TAG_RE = re.compile(
    r"[\s\-,]+(?:"
    + "|".join([
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    ])
    + r")\s*$",
    re.IGNORECASE,
)

# ── punctuation handling ──────────────────────────────────────────────────────
# Apostrophes and similar quote chars are *removed* (not replaced with a space)
# so "Children's" -> "childrens" rather than "children s".
# Everything else (periods, commas, dashes, slashes, etc.) -> space.
#
# _APOS_RE covers:
#   U+0027  '   straight apostrophe
#   U+2018  '   left single quotation mark (curly open)
#   U+2019  '   right single quotation mark (curly close)
#   U+0060  `   backtick
_APOS_RE       = re.compile("['‘’`]")
_PUNCT_RE      = re.compile(r"[.,\-/&+]")   # other punctuation -> space
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    """
    Return a canonical lowercase key for name comparison.

    Steps applied in order:
      1. Strip leading/trailing whitespace.
      2. Remove a leading article ("The ", "A ", "An ").
      3. Remove an embedded state abbreviation tag at the end (e.g. "- FL").
      4. Strip corporate/legal suffixes (Inc, LLC, Foundation, d/b/a ..., etc.)
         repeatedly until none remain (handles "Inc., LLC" double-suffix cases).
      5. Remove apostrophes/backticks; replace other punctuation with a space.
      6. Collapse internal whitespace and lowercase.
    """
    s = name.strip()

    # 1. Leading article
    s = _LEADING_ARTICLE_RE.sub("", s)

    # 2. State abbreviation tag
    s = _STATE_TAG_RE.sub("", s)

    # 3. Corporate suffixes -- loop to handle stacked suffixes ("Fund, Inc., LLC")
    prev = None
    while prev != s:
        prev = s
        s = _SUFFIX_RE.sub("", s)

    # 4. Apostrophes -> removed; other punctuation -> space; collapse and lowercase
    s = _APOS_RE.sub("", s)
    s = _PUNCT_RE.sub(" ", s)
    s = _WHITESPACE_RE.sub(" ", s).strip().lower()

    return s


def is_same_org(a: str, b: str) -> bool:
    """
    Return True if two org name strings refer to the same organization.

    Comparison is done on normalized keys (see normalize_name), so differences
    in articles, corporate suffixes, punctuation, and whitespace are ignored.
    """
    return normalize_name(a) == normalize_name(b)
