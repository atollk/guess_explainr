import asyncio
import io
import time as _time

import requests as _requests
import streetview
import streetview.download as _sv_dl
from litestar import get
from litestar.exceptions import NotFoundException
from litestar.response import Response
from streetview_dl import StreetViewDownloader

from guess_explainr import state

# ---------------------------------------------------------------------------
# Patch streetview's HTTP client to send browser-like headers (avoids 403s)
# and to sleep between tile fetches.
# ---------------------------------------------------------------------------


class _BrowserSession:
    """Drop-in replacement for the requests module inside streetview.download.
    Sends browser-like headers and exposes module-level exception classes."""

    ConnectionError = _requests.ConnectionError

    def __init__(self) -> None:
        self._session = _requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.google.com/maps/",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            }
        )

    def get(self, *args, **kwargs):
        return self._session.get(*args, **kwargs)


_sv_dl.requests = _BrowserSession()  # pyrefly: ignore[bad-assignment]

# Seconds to wait between individual tile fetches (helps avoid 403s from Google).
PANORAMA_TILE_DELAY: float = 1

_original_fetch_tile = _sv_dl.fetch_panorama_tile


def _fetch_tile_with_delay(tile_info, max_retries=_sv_dl.DEFAULT_MAX_RETRIES):
    _time.sleep(PANORAMA_TILE_DELAY)
    return _original_fetch_tile(tile_info, max_retries)


_sv_dl.fetch_panorama_tile = _fetch_tile_with_delay


# ---------------------------------------------------------------------------
# Fetch + cache
# ---------------------------------------------------------------------------


class PanoramaFetchError(Exception):
    pass


def _fetch_via_official_api(panorama_id: str, maps_api_key: str) -> None:
    """Download using the official Maps Tiles API via streetview-dl."""
    try:
        downloader = StreetViewDownloader(api_key=maps_api_key)
        metadata = downloader.get_metadata(pano_id=panorama_id)
        img = downloader.download_panorama(metadata, quality="low")
    except Exception as e:
        raise PanoramaFetchError(
            f"Could not download the Street View image via the official API: {e}"
        ) from e
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    state.panorama_state.panorama_image_bytes = buf.getvalue()


def _fetch_via_scraping(panorama_id: str) -> None:
    """Download by scraping (no API key required, but may be blocked)."""
    try:
        img = streetview.get_panorama(pano_id=panorama_id, zoom=2, multi_threaded=False)
    except Exception as e:
        raise PanoramaFetchError(
            "Could not download the Street View image — Google may be blocking the request."
        ) from e
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    state.panorama_state.panorama_image_bytes = buf.getvalue()


async def fetch_and_cache(panorama_id: str) -> None:
    """Download the Street View panorama and store JPEG bytes in state.

    Uses the official Maps Tiles API if a Maps API key is configured,
    otherwise falls back to scraping.

    Raises PanoramaFetchError on failure.
    """
    maps_api_key = state.get_config().maps_api_key

    def _blocking() -> None:
        if maps_api_key:
            _fetch_via_official_api(panorama_id, maps_api_key)
        else:
            _fetch_via_scraping(panorama_id)

    await asyncio.to_thread(_blocking)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@get("/panorama-image", media_type="image/jpeg")
async def panorama_image() -> Response[bytes]:
    img = state.panorama_state.panorama_image_bytes
    if not img:
        raise NotFoundException(detail="No panorama image available")
    return Response(content=img, media_type="image/jpeg")
