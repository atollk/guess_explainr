from guess_explainr.routes.step2 import (
    GoogleMapsLocation,
    _display_name,
    _flag,
)

# A real-looking Google Maps Street View share URL.
# After URL-decoding, the embedded panoid= query parameter is present.
FULL_URL = (
    "https://www.google.com/maps/@38.0691925,22.2390295,3a,90y,302.4h,92.61t"
    "/data=!3m7!1e1!3m5!1sC7dD4mGuuHHm6SjUq80gtw!2e0"
    "!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail"
    "%3Fcb_client%3Dmaps_sv.tactile%26w%3D900%26h%3D600%26pitch%3D-2.61"
    "%26panoid%3DC7dD4mGuuHHm6SjUq80gtw%26yaw%3D302.40146!7i16384!8i8192"
)

EXPECTED_PANO_ID = "C7dD4mGuuHHm6SjUq80gtw"


# ---------------------------------------------------------------------------
# GoogleMapsLocation.parse
# ---------------------------------------------------------------------------


def test_parse_panorama_id():
    loc = GoogleMapsLocation.parse(FULL_URL)
    assert loc.panorama_id == EXPECTED_PANO_ID


def test_parse_coordinates():
    loc = GoogleMapsLocation.parse(FULL_URL)
    assert abs(loc.latitude - 38.0691925) < 1e-4
    assert abs(loc.longitude - 22.2390295) < 1e-4


def test_parse_no_panorama_id():
    url = "https://www.google.com/maps/@48.8566,2.3522,12z"
    loc = GoogleMapsLocation.parse(url)
    assert loc.panorama_id == ""


def test_parse_no_coords():
    loc = GoogleMapsLocation.parse("https://example.com")
    assert loc.latitude == 0.0
    assert loc.longitude == 0.0


def test_parse_negative_coords():
    url = "https://www.google.com/maps/@-33.8688,151.2093,3a"
    loc = GoogleMapsLocation.parse(url)
    assert abs(loc.latitude - (-33.8688)) < 1e-4
    assert abs(loc.longitude - 151.2093) < 1e-4


# ---------------------------------------------------------------------------
# _flag
# ---------------------------------------------------------------------------


def test_flag_us():
    assert _flag("US") == "🇺🇸"


def test_flag_de():
    assert _flag("DE") == "🇩🇪"


def test_flag_lowercase():
    # Should handle lowercase input
    assert _flag("fr") == "🇫🇷"


# ---------------------------------------------------------------------------
# _display_name
# ---------------------------------------------------------------------------


def test_display_name_iso_country():
    name = _display_name("france")
    assert "🇫🇷" in name
    assert "France" in name


def test_display_name_multi_word():
    name = _display_name("south-korea")
    assert "🇰🇷" in name
    assert "South Korea" in name


def test_display_name_custom_emoji():
    assert "🧙" in _display_name("middle-earth")


def test_display_name_unknown_slug():
    # Unknown slug gets the fallback flag
    name = _display_name("unknown-slug")
    assert "🏳️" in name
