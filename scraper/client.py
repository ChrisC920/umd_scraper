from __future__ import annotations

import time

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

BASE = "http://nutrition.umd.edu"
UA = "umd-nutrition-scraper/1.0 (+https://github.com/ChrisC920/umd_scraper)"


class Client:
    def __init__(self, base: str = BASE, min_interval: float = 0.5):
        self.base = base
        self.min_interval = min_interval
        self._last = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})

    def _throttle(self) -> None:
        delta = time.monotonic() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.monotonic()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def get(self, path: str, params: dict | None = None, timeout: int = 30) -> str:
        self._throttle()
        url = path if path.startswith("http") else f"{self.base}/{path.lstrip('/')}"
        r = self.session.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.text

    def longmenu(self, location_num: int, dtdate: str, meal: str) -> str:
        return self.get(
            "longmenu.aspx",
            params={"locationNum": location_num, "dtdate": dtdate, "mealName": meal},
        )

    def label(self, rec_num: int, portion: int) -> str:
        return self.get("label.aspx", params={"RecNumAndPort": f"{rec_num}*{portion}"})
