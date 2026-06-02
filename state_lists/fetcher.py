"""
HTTP session, raw-bytes fetcher, and URL-reachability checker.

Session-priming strategy
------------------------
Some government sites gate access behind a session cookie that is only set
when you land on the homepage first (e.g. a WAF issues a challenge cookie on
the first request and expects it on subsequent ones).  _prime_session() makes
one silent GET to the site's origin (scheme + host) the first time we see a
new domain, so the session picks up any such cookies before we hit the real
target URL.  Already-visited origins are cached in _primed_domains so we only
pay the extra round-trip once per domain per process run.
"""
import threading

import requests
import urllib3
from dataclasses import dataclass
from urllib.parse import urlparse

from sources import HEADERS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()  # reuse TCP connections and cookies across all requests

_primed_domains: set[str] = set()
_prime_lock = threading.Lock()  # guards _primed_domains for concurrent fetch_bytes calls


def _prime_session(url: str) -> None:
    """
    Visit the homepage of url's domain once to pick up session/gating cookies.

    The visit is best-effort: any error is silently swallowed so a blocked or
    slow homepage never prevents us from attempting the real target URL.

    Thread-safe: the domain is added to _primed_domains inside the lock before
    the actual request so only one thread ever primes a given origin.
    """
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    with _prime_lock:
        if origin in _primed_domains:
            return
        _primed_domains.add(origin)
    # Lock is released before the network call — only this thread primes the origin
    try:
        session.get(origin, headers=HEADERS, timeout=10, allow_redirects=True, verify=False)
    except Exception:
        pass  # best-effort; don't let a homepage failure block the real request


@dataclass
class Result:
    url: str
    status: int | None
    blocked: bool | None  # True=blocked, False=OK, None=connection failed
    reason: str


def fetch_bytes(url: str) -> bytes:
    """
    Download raw bytes from url.  Primes the session on the first visit to
    each domain.  Raises requests.HTTPError on non-2xx.
    """
    _prime_session(url)
    r = session.get(url, headers=HEADERS, timeout=15, allow_redirects=True, verify=False)
    r.raise_for_status()
    return r.content


def check_site(url: str) -> Result:
    """
    Return a Result describing whether url is accessible.  Primes the session
    on the first visit to each domain so gating cookies are present.
    """
    _prime_session(url)
    try:
        r = session.get(url, headers=HEADERS, timeout=10, allow_redirects=True, verify=False)
        html = r.text.lower()

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
