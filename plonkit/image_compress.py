"""Resize and JPEG-compress images before embedding in PDFs."""

import io

from PIL import Image

_MAX_WIDTH = 800  # px — wide enough for A4 print, small enough to stay compact
_JPEG_QUALITY = 80


def compress(data: bytes, *, max_width: int = _MAX_WIDTH, quality: int = _JPEG_QUALITY) -> bytes:
    """Resize *data* to at most *max_width* pixels wide and re-encode as JPEG.

    Transparent images (RGBA, P with transparency) are composited onto a white
    background before JPEG encoding, since JPEG has no alpha channel.

    Returns the compressed JPEG bytes.
    """
    img = Image.open(io.BytesIO(data))

    # Resize preserving aspect ratio
    if img.width > max_width:
        new_height = round(img.height * max_width / img.width)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    # Flatten transparency onto white (JPEG cannot encode alpha)
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.getchannel("A"))
        img = background
    elif img.mode == "P":
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.getchannel("A"))
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()
