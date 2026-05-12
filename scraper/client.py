from __future__ import annotations

import os
import threading
import time

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DEFAULT_BASE = "http://nutrition.umd.edu"
BASE = os.environ.get("SCRAPER_BASE_URL", DEFAULT_BASE)
UA = "umd-nutrition-scraper/1.0 (+https://github.com/ChrisC920/umd_scraper)"


class SnapshotMissing(Exception):
    """Wayback has no snapshot for this URL (redirects to /save/). Not retryable."""


class Client:
    def __init__(self, base: str = BASE, min_interval: float = 0.5):
        self.base = base.rstrip("/")
        self.min_interval = min_interval
        self._last = 0.0
        self._lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})

    def _throttle(self) -> None:
        with self._lock:
            delta = time.monotonic() - self._last
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last = time.monotonic()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=5, max=120),
        # Retry on transient HTTP errors but NOT on SnapshotMissing.
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def get(self, path: str, params: dict | None = None, timeout: int = 60) -> str:
        self._throttle()
        url = path if path.startswith("http") else f"{self.base}/{path.lstrip('/')}"
        # allow_redirects=False so Wayback /save/ fallback doesn't masquerade as a real fetch.
        r = self.session.get(url, params=params, timeout=timeout, allow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("location", "")
            if "/save/" in loc or "/save_" in loc:
                # Snapshot missing — Wayback wants to save it. Treat as missing label, not retryable.
                raise SnapshotMissing(url)
            # Follow benign redirects (e.g. to a nearby capture).
            next_url = loc if loc.startswith("http") else f"{self.base}/{loc.lstrip('/')}"
            r = self.session.get(next_url, timeout=timeout, allow_redirects=True)
        if r.status_code == 429:
            ra = r.headers.get("Retry-After")
            if ra and ra.isdigit():
                time.sleep(min(int(ra), 60))
            r.raise_for_status()
        r.raise_for_status()
        return r.text

    def longmenu(self, location_num: int, dtdate: str, meal: str) -> str:
        return self.get(
            "longmenu.aspx",
            params={"locationNum": location_num, "dtdate": dtdate, "mealName": meal},
        )

    def label(self, rec_num: int, portion: int) -> str:
        return self.get("label.aspx", params={"RecNumAndPort": f"{rec_num}*{portion}"})
