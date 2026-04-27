"""On-the-fly download and caching of PlonkIt country guide PDFs from GitHub.

In dev mode (PLONKIT_LOCAL=1) the local /plonkit/ directory at the repo root
is used directly — no network access, no cache.

In production, PDFs are cached at platformdirs.user_cache_dir("guess_explainr")/plonkit/.
On startup, sync_plonkit_files() checks whether metadata.json changed on GitHub
(one API call).  Only if it changed are individual PDFs compared and re-downloaded.
"""

import asyncio
import contextlib
import json
import logging
import os
from pathlib import Path

import niquests
import platformdirs

from guess_explainr import state

logger = logging.getLogger(__name__)

_GITHUB_OWNER = "atollk"
_GITHUB_REPO = "guess_explainr"
_GITHUB_BRANCH = "main"
_GITHUB_DIR = "plonkit"
_CONCURRENCY = 8

_GITHUB_API_BASE = (
    f"https://api.github.com/repos/{_GITHUB_OWNER}/{_GITHUB_REPO}/contents/{_GITHUB_DIR}"
)
_GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{_GITHUB_OWNER}/{_GITHUB_REPO}/{_GITHUB_BRANCH}/{_GITHUB_DIR}"

# Dev: repo root /plonkit/ (up 3 levels: plonkit_cache.py → guess_explainr → src → repo root)
_DEV_PATH = Path(__file__).parent.parent.parent / "plonkit"
# Production: platform cache dir
_CACHE_PATH = Path(platformdirs.user_cache_dir("guess_explainr")) / "plonkit"
# Tracks the GitHub blob SHA of metadata.json so we can detect changes with one API call
_MANIFEST_FILE = _CACHE_PATH / "manifest.json"


def get_plonkit_dir() -> Path:
    """Return the directory PDFs are loaded from (dev local or cache)."""
    if os.environ.get("PLONKIT_LOCAL"):
        return _DEV_PATH
    return _CACHE_PATH


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_manifest() -> dict[str, str]:
    """Load {key: value} tracking data from the local manifest file."""
    try:
        return json.loads(_MANIFEST_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_manifest(data: dict[str, str]) -> None:
    _MANIFEST_FILE.write_text(json.dumps(data))


async def _get_remote_metadata_sha() -> str:
    """One GitHub Contents API call → blob SHA of plonkit/metadata.json."""
    url = f"{_GITHUB_API_BASE}/metadata.json"
    async with niquests.AsyncSession() as s:
        r = await s.get(url, headers={"Accept": "application/vnd.github+json"})
        r.raise_for_status()
        return r.json()["sha"]


async def _download_json(raw_path: str) -> dict:
    async with niquests.AsyncSession() as s:
        r = await s.get(f"{_GITHUB_RAW_BASE}/{raw_path}")
        r.raise_for_status()
        return r.json()


async def _download_pdf(slug: str, dest: Path, sem: asyncio.Semaphore) -> None:
    async with sem, niquests.AsyncSession() as s:
        r = await s.get(f"{_GITHUB_RAW_BASE}/{slug}.pdf")
        r.raise_for_status()
        if r.content is not None:
            dest.write_bytes(r.content)  # pyrefly: ignore[bad-argument-type]


# ---------------------------------------------------------------------------
# Public startup task
# ---------------------------------------------------------------------------


async def sync_plonkit_files() -> None:
    """Check GitHub for PlonkIt guide updates and download any changed PDFs.

    Updates state.plonkit_sync_state as work progresses.
    Called as an asyncio background task from app.py on_startup.
    """
    if os.environ.get("PLONKIT_LOCAL"):
        state.plonkit_sync_state.ready = True
        return

    _CACHE_PATH.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()

    # --- Step 1: one API call to check if metadata.json changed ---
    try:
        remote_sha = await _get_remote_metadata_sha()
    except Exception as exc:
        logger.warning("Could not reach GitHub for PlonkIt manifest: %s", exc)
        if any(_CACHE_PATH.glob("*.pdf")):
            logger.info("Falling back to cached PlonkIt PDFs.")
            state.plonkit_sync_state.ready = True
        else:
            state.plonkit_sync_state.error = (
                "Could not download country guides and no local cache found. "
                "Check your internet connection."
            )
        return

    if manifest.get("metadata_sha") == remote_sha:
        # Nothing changed — cached PDFs are up to date
        state.plonkit_sync_state.ready = True
        return

    # --- Step 2: metadata.json changed — find which PDFs need updating ---
    try:
        remote_metadata: dict[str, dict] = await _download_json("metadata.json")
    except Exception as exc:
        logger.warning("Could not download PlonkIt metadata.json: %s", exc)
        state.plonkit_sync_state.error = "Failed to fetch country guide metadata."
        return

    cached_metadata_path = _CACHE_PATH / "metadata.json"
    local_metadata: dict[str, dict] = {}
    if cached_metadata_path.exists():
        with contextlib.suppress(json.JSONDecodeError):
            local_metadata = json.loads(cached_metadata_path.read_text())

    to_download = [
        slug
        for slug, info in remote_metadata.items()
        if (
            local_metadata.get(slug, {}).get("last_update") != info.get("last_update")
            or not (_CACHE_PATH / f"{slug}.pdf").exists()
        )
    ]

    state.plonkit_sync_state.total = len(to_download)
    state.plonkit_sync_state.done = 0

    # --- Step 3: download changed PDFs in parallel ---
    if to_download:
        sem = asyncio.Semaphore(_CONCURRENCY)

        async def _dl(slug: str) -> None:
            try:
                await _download_pdf(slug, _CACHE_PATH / f"{slug}.pdf", sem)
            except Exception as exc:
                logger.warning("Failed to download %s.pdf: %s", slug, exc)
            state.plonkit_sync_state.done += 1

        await asyncio.gather(*[_dl(slug) for slug in to_download])

    # --- Step 4: persist updated metadata and manifest ---
    cached_metadata_path.write_text(json.dumps(remote_metadata))
    _save_manifest({"metadata_sha": remote_sha})
    state.plonkit_sync_state.ready = True
