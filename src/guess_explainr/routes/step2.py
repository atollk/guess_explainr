import asyncio
import dataclasses
import glob
import json
import re
import urllib.parse
import uuid
from dataclasses import dataclass

from geopy import Location
from geopy.geocoders import Nominatim
from litestar import post
from litestar.exceptions import HTTPException
from litestar.response import Template

from guess_explainr import state
from guess_explainr.models import ProcessUrlRequest
from guess_explainr.routes.panorama import PanoramaFetchError, fetch_and_cache


@dataclass
class _Country:
    id: str
    display_name: str


def _flag(code: str) -> str:
    """Convert a 2-letter ISO 3166-1 alpha-2 code to an emoji flag."""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


# Maps plonkit slug → ISO 3166-1 alpha-2 code.
# Territories sharing a code (alaska, hawaii, azores, madeira) are listed before
# their parent country so the inversion below naturally picks the parent.
# Non-ISO entries use None and get a custom emoji via _CUSTOM_EMOJI.
_COUNTRY_ISO: dict[str, str | None] = {
    "alaska": "US",
    "hawaii": "US",
    "azores": "PT",
    "madeira": "PT",
    "middle-earth": None,
    "spillover-countries": None,
    "albania": "AL",
    "american-samoa": "AS",
    "andorra": "AD",
    "antarctica": "AQ",
    "argentina": "AR",
    "australia": "AU",
    "austria": "AT",
    "bangladesh": "BD",
    "belarus": "BY",
    "belgium": "BE",
    "bermuda": "BM",
    "bhutan": "BT",
    "bolivia": "BO",
    "botswana": "BW",
    "brazil": "BR",
    "british-indian-ocean-territory": "IO",
    "bulgaria": "BG",
    "cambodia": "KH",
    "canada": "CA",
    "chile": "CL",
    "china": "CN",
    "christmas-island": "CX",
    "cocos-islands": "CC",
    "colombia": "CO",
    "costa-rica": "CR",
    "croatia": "HR",
    "curacao": "CW",
    "cyprus": "CY",
    "czechia": "CZ",
    "denmark": "DK",
    "dominican-republic": "DO",
    "ecuador": "EC",
    "egypt": "EG",
    "estonia": "EE",
    "eswatini": "SZ",
    "falkland-islands": "FK",
    "faroe-islands": "FO",
    "finland": "FI",
    "france": "FR",
    "germany": "DE",
    "ghana": "GH",
    "gibraltar": "GI",
    "greece": "GR",
    "greenland": "GL",
    "guam": "GU",
    "guatemala": "GT",
    "hong-kong": "HK",
    "hungary": "HU",
    "iceland": "IS",
    "india": "IN",
    "indonesia": "ID",
    "iraq": "IQ",
    "ireland": "IE",
    "isle-of-man": "IM",
    "israel-west-bank": "IL",
    "italy": "IT",
    "japan": "JP",
    "jersey": "JE",
    "jordan": "JO",
    "kazakhstan": "KZ",
    "kenya": "KE",
    "kyrgyzstan": "KG",
    "laos": "LA",
    "latvia": "LV",
    "lebanon": "LB",
    "lesotho": "LS",
    "liechtenstein": "LI",
    "lithuania": "LT",
    "luxembourg": "LU",
    "macau": "MO",
    "madagascar": "MG",
    "malaysia": "MY",
    "mali": "ML",
    "malta": "MT",
    "martinique": "MQ",
    "mexico": "MX",
    "monaco": "MC",
    "mongolia": "MN",
    "montenegro": "ME",
    "namibia": "NA",
    "nepal": "NP",
    "netherlands": "NL",
    "new-zealand": "NZ",
    "nigeria": "NG",
    "north-macedonia": "MK",
    "northern-mariana-islands": "MP",
    "norway": "NO",
    "oman": "OM",
    "pakistan": "PK",
    "panama": "PA",
    "peru": "PE",
    "philippines": "PH",
    "pitcairn-islands": "PN",
    "poland": "PL",
    "portugal": "PT",
    "puerto-rico": "PR",
    "qatar": "QA",
    "reunion": "RE",
    "romania": "RO",
    "russia": "RU",
    "rwanda": "RW",
    "saint-pierre-and-miquelon": "PM",
    "san-marino": "SM",
    "sao-tome-and-principe": "ST",
    "senegal": "SN",
    "serbia": "RS",
    "singapore": "SG",
    "slovakia": "SK",
    "slovenia": "SI",
    "south-africa": "ZA",
    "south-georgia-sandwich-islands": "GS",
    "south-korea": "KR",
    "spain": "ES",
    "sri-lanka": "LK",
    "svalbard": "SJ",
    "sweden": "SE",
    "switzerland": "CH",
    "taiwan": "TW",
    "tanzania": "TZ",
    "thailand": "TH",
    "tunisia": "TN",
    "turkey": "TR",
    "uganda": "UG",
    "ukraine": "UA",
    "united-arab-emirates": "AE",
    "united-kingdom": "GB",
    "united-states": "US",
    "uruguay": "UY",
    "us-minor-outlying-islands": "UM",
    "us-virgin-islands": "VI",
    "vanuatu": "VU",
    "vietnam": "VN",
}

_CUSTOM_EMOJI: dict[str, str] = {
    "middle-earth": "🧙",
    "spillover-countries": "🌍",
}

# ISO alpha-2 → canonical plonkit slug (last write wins, so parent countries
# defined after their territories naturally take precedence).
_ISO_TO_SLUG: dict[str, str] = {iso: slug for slug, iso in _COUNTRY_ISO.items() if iso}


def _display_name(slug: str) -> str:
    iso = _COUNTRY_ISO.get(slug)
    emoji = _flag(iso) if iso else _CUSTOM_EMOJI.get(slug, "🏳️")
    return f"{emoji} {slug.replace('-', ' ').title()}"


def _load_country_list() -> list[_Country]:
    plonkit_path = "src/guess_explainr/static/files/plonkit"
    pdf_files = glob.glob("*.pdf", root_dir=plonkit_path)
    return [
        _Country(id=slug, display_name=_display_name(slug))
        for file in pdf_files
        if (slug := file.replace(".pdf", ""))
    ]


COUNTRIES = sorted(_load_country_list(), key=lambda x: x.display_name)


@dataclass
class GoogleMapsLocation:
    panorama_id: str
    latitude: float
    longitude: float

    @staticmethod
    def parse(url: str) -> "GoogleMapsLocation":
        # https://www.google.com/maps/@38.0691925,22.2390295,3a,90y,302.4h,92.61t/data=!3m7!1e1!3m5!1sC7dD4mGuuHHm6SjUq80gtw!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fcb_client%3Dmaps_sv.tactile%26w%3D900%26h%3D600%26pitch%3D-2.612560000000002%26panoid%3DC7dD4mGuuHHm6SjUq80gtw%26yaw%3D302.40146!7i16384!8i8192?entry=ttu&g_ep=EgoyMDI2MDEwNC4wIKXMDSoASAFQAw%3D%3D
        url_decoded = urllib.parse.unquote(url)

        panorama_id = ""
        if (m := re.search(r"panoid=([^!&]+)", url_decoded)) or (
            m := re.search(r"!1s([^!]+)!", url)
        ):
            panorama_id = m.group(1)

        if m := re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url_decoded):
            latitude, longitude = float(m.group(1)), float(m.group(2))
        else:
            latitude = longitude = 0.0

        return GoogleMapsLocation(panorama_id=panorama_id, latitude=latitude, longitude=longitude)


_geolocator = Nominatim(user_agent="guess_explainr/0.1")


async def _country_from_coords(lat: float, lon: float) -> _Country | None:
    """Return the display_name for the country at lat/lon, or '' on failure."""
    result = await asyncio.to_thread(_geolocator.reverse, (lat, lon), zoom=3, language="en")
    if result is None:
        return None
    if isinstance(result, list):
        result = result[0]
    assert isinstance(result, Location)
    iso = result.raw.get("address", {}).get("country_code", "").upper()
    slug = _ISO_TO_SLUG.get(iso, "")
    return next((country for country in COUNTRIES if country.id == slug), None)


@post("/process-url")
async def process_url(data: ProcessUrlRequest) -> Template:
    location = GoogleMapsLocation.parse(data.url)
    state.in_memory_state.panorama_id = location.panorama_id
    state.in_memory_state.panorama_image_bytes = None

    try:
        country, _ = await asyncio.gather(
            _country_from_coords(location.latitude, location.longitude),
            fetch_and_cache(location.panorama_id) if location.panorama_id else asyncio.sleep(0),
        )
    except PanoramaFetchError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if country is None:
        country = _Country(id="", display_name="")
    return Template(
        template_name="partials/step3_content.html",
        context={
            "detected_country": country,
            "available_countries": COUNTRIES,
            "available_countries_json": json.dumps([dataclasses.asdict(c) for c in COUNTRIES]),
            "panorama_available": state.in_memory_state.panorama_image_bytes is not None,
            "panorama_token": uuid.uuid4().hex,
        },
    )


def extract_panorama_id(url: str) -> str:
    """Extract the Street View panorama ID from a Google Maps URL."""
    url_decoded = urllib.parse.unquote(url)
    match = re.search("panoid=([^!]+)[&$]", url_decoded)
    if match:
        return match.group(1)
    match = re.search(r"!1s([^!]+)!", url)
    if match:
        return match.group(1)
    return ""
