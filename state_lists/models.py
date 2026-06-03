"""
Data model for a Scholarship Granting Organization (SGO) record.

Every parser in the state_lists pipeline produces a list of SGO instances.
The dataclass is intentionally flat — one row per org — so it maps directly
to a CSV row via dataclasses.asdict().
"""
from dataclasses import dataclass, field


@dataclass
class SGO:
    state: str          # two-letter state code, e.g. "OH"
    name: str           # organization name
    ein: str | None     # IRS EIN if available, e.g. "12-3456789"
    raw_source: str     # URL this record came from
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    known: str = ""        # "Yes" if this org is already a validated/certified SGO

    def __post_init__(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError(f"SGO name must not be empty (state={self.state}, source={self.raw_source})")
        if len(self.name) > 300:
            raise ValueError(f"SGO name unexpectedly long ({len(self.name)} chars): {self.name[:80]!r}")
