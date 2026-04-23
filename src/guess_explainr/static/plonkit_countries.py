"""Fetch the list of country slugs available on plonkit.net."""

import json
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup

_GUIDE_URL = "https://www.plonkit.net/guide"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


@dataclass
class Country:
    slug: str
    last_updated: datetime


def fetch_countries() -> list[Country]:
    """Return a sorted list of countries found on the plonkit.net guide page.

    Example return value:
        [Country(slug="botswana", last_updated=datetime(...)), ...]
    """
    response = requests.get(_GUIDE_URL, headers=_HEADERS, timeout=15)
    response.raise_for_status()

    # The page is a JS SPA; country data is embedded in a <script id="__PRELOADED_DATA__">
    # JSON block so BeautifulSoup can read it without a headless browser.
    soup = BeautifulSoup(response.text, "html.parser")
    script_tag = soup.find("script", id="__PRELOADED_DATA__")
    if script_tag is None:
        raise RuntimeError("Could not find __PRELOADED_DATA__ script tag on the page")

    payload = json.loads(script_tag.string or "")
    if not payload.get("success"):
        raise RuntimeError(f"Unexpected payload: {payload}")

    exclude = {"maps", "beginners-guide"}
    countries = [
        Country(
            slug=entry["slug"],
            last_updated=datetime.fromisoformat(entry["updatedAt"].replace("Z", "+00:00")),
        )
        for entry in payload["data"]
        if entry.get("slug") and entry["slug"] not in exclude
    ]
    return sorted(countries, key=lambda c: c.slug)


if __name__ == "__main__":
    countries = fetch_countries()
    print(f"Found {len(countries)} countries:")
    for c in countries:
        print(f"  {c.slug:30s}  {c.last_updated.strftime('%Y-%m-%d')}")
