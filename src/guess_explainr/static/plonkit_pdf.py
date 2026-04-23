"""Generate PDFs of plonkit.net country guides using Docker + weasyprint."""

import base64
import json
import re
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_BASE_URL = "https://www.plonkit.net"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_page_data(slug: str) -> dict:
    r = requests.get(f"{_BASE_URL}/{slug}", headers=_HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    script = soup.find("script", id="__PRELOADED_DATA__")
    if script is None:
        raise RuntimeError(f"No __PRELOADED_DATA__ found for slug {slug!r}")
    return json.loads(script.string or "")["data"]["public"]


def _image_data_uri(
    url: str, image_transform: Callable[[bytes], bytes] | None = None
) -> str | None:
    """Download an image and return it as a base64 data URI, or None on failure.

    If *image_transform* is provided it is called on the raw response bytes
    before encoding; the returned bytes are assumed to be JPEG.
    """
    full = url if url.startswith("http") else _BASE_URL + url
    try:
        r = requests.get(full, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        if image_transform is not None:
            data = image_transform(r.content)
            mime = "image/jpeg"
        else:
            data = r.content
            mime = r.headers.get("Content-Type", "image/png").split(";")[0].strip()
        b64 = base64.b64encode(data).decode()
        return f"data:{mime};base64,{b64}"
    except Exception as exc:
        print(f"  WARN: could not fetch {full}: {exc}")
        return None


def _md_to_html(text: str) -> str:
    """Convert the limited markdown used on plonkit to HTML fragments."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    if text.startswith("NOTE:"):
        text = f'<span class="note">{text}</span>'
    elif text.startswith("RESOURCE:"):
        text = f'<span class="resource">{text}</span>'
    return text


_HTML_CSS = """
body {
  font-family: Georgia, "Times New Roman", serif;
  font-size: 11pt;
  color: #1a1a1a;
  margin: 0;
  padding: 24px 36px;
  line-height: 1.55;
}
h1 {
  font-size: 28pt;
  color: #0d1f40;
  margin: 0 0 8px 0;
}
h2 {
  font-size: 14pt;
  color: #1a3a6e;
  border-bottom: 2px solid #c8d0e0;
  padding-bottom: 5px;
  margin: 28px 0 14px 0;
  page-break-after: avoid;
}
.hero {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  display: block;
  margin-bottom: 22px;
  border-radius: 6px;
}
.tip {
  display: flex;
  gap: 18px;
  margin-bottom: 18px;
  align-items: flex-start;
  page-break-inside: avoid;
}
.tip img {
  flex-shrink: 0;
  border-radius: 4px;
  object-fit: contain;
  max-height: 180px;
}
.tip-text {
  flex: 1;
  font-size: 10pt;
}
.tip-text p {
  margin: 0 0 6px 0;
}
.centered-img {
  text-align: center;
  margin: 14px 0;
  page-break-inside: avoid;
}
.centered-img img {
  max-width: 72%;
  max-height: 320px;
  object-fit: contain;
}
.note {
  color: #555;
  font-style: italic;
  font-size: 9.5pt;
}
.resource {
  color: #334466;
  font-size: 9.5pt;
}
.map-section {
  background: #f4f4ef;
  border-left: 4px solid #99a8bb;
  padding: 10px 16px;
  margin: 10px 0;
  border-radius: 0 4px 4px 0;
  font-size: 10pt;
}
.map-section p { margin: 5px 0; }
"""


def _build_html(data: dict, image_transform: Callable[[bytes], bytes] | None = None) -> str:
    def img_uri(url: str) -> str | None:
        return _image_data_uri(url, image_transform)

    parts: list[str] = [
        f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
        f"<style>{_HTML_CSS}</style></head><body>",
        f"<h1>{data['title']}</h1>",
    ]

    if data.get("heroImage"):
        uri = img_uri(data["heroImage"])
        if uri:
            parts.append(f'<img class="hero" src="{uri}">')

    for step in data["steps"]:
        title = step.get("title", "")
        parts.append(f"<h2>{title}</h2>")

        if step["kind"] == "map":
            parts.append('<div class="map-section">')
            for line in step.get("text", []):
                parts.append(f"<p>{_md_to_html(line)}</p>")
            parts.append("</div>")
            continue

        for item in step.get("items", []):
            if item["kind"] == "centeredImage":
                uri = img_uri(item["imageUrl"])
                if uri:
                    parts.append(f'<div class="centered-img"><img src="{uri}"></div>')

            elif item["kind"] == "tip":
                d = item["data"]
                img_info = d.get("image", {})
                img_url = img_info.get("imageUrl", "")
                width_frac = img_info.get("width", 0.5)
                texts = d.get("text", [])

                img_html = ""
                if img_url:
                    uri = img_uri(img_url)
                    if uri:
                        img_w_pct = int(width_frac * 100)
                        img_html = (
                            f'<img src="{uri}" '
                            f'style="width:{img_w_pct}%; max-height:200px; object-fit:contain;">'
                        )

                text_html = "".join(f"<p>{_md_to_html(t)}</p>" for t in texts)
                parts.append(
                    f'<div class="tip">{img_html}<div class="tip-text">{text_html}</div></div>'
                )

    parts.append("</body></html>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_country_guide_pdf(
    slug: str,
    output_path: str | Path,
    image_transform: Callable[[bytes], bytes] | None = None,
) -> Path:
    """Generate a PDF for a plonkit country guide using Docker/Podman + weasyprint.

    Builds an HTML document from the embedded JSON data (all images inlined as
    base64), then passes it to the minidocks/weasyprint container image.

    *image_transform*, if provided, is called on the raw bytes of every downloaded
    image before base64-encoding.  Use it to resize/compress images, e.g.::

        from image_compress import compress
        fetch_country_guide_pdf("botswana", "out.pdf", image_transform=compress)

    Requires Docker or Podman to be running.
    """
    output_path = Path(output_path)
    print(f"Fetching data for {slug!r}...")
    data = _fetch_page_data(slug)
    image_count = sum(1 for s in data["steps"] for _ in s.get("items", [])) + 1
    print(f"Building HTML (downloading up to {image_count} images)...")
    html = _build_html(data, image_transform)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "guide.html").write_text(html, encoding="utf-8")

        runner = (
            "docker"
            if subprocess.run(["which", "docker"], capture_output=True).returncode == 0
            else "podman"
        )
        print(f"Running weasyprint via {runner}...")
        subprocess.run(
            [
                runner,
                "run",
                "--rm",
                "--privileged",  # needed for /dev/stdout on rootless podman
                "-v",
                f"{tmpdir}:/work",
                "minidocks/weasyprint",
                "/work/guide.html",
                "/work/guide.pdf",
            ],
            check=True,
        )

        output_path.write_bytes((tmp / "guide.pdf").read_bytes())

    print(f"Saved → {output_path}")
    return output_path


if __name__ == "__main__":
    import sys

    slug = sys.argv[1] if len(sys.argv) > 1 else "botswana"
    fetch_country_guide_pdf(slug, f"./plonkit_{slug}.pdf")
