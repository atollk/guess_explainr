import asyncio
import webbrowser

import browser_cookie3

_COOKIE_NAME = "_ncfa"
_DOMAIN = "geoguessr.com"
_SIGNIN_URL = "https://www.geoguessr.com/signin"
_POLL_INTERVAL = 1.0  # seconds between cookie checks
_TIMEOUT = 120  # seconds before TimeoutError


def _read_ncfa() -> str | None:
    """Try each installed browser in order; return _ncfa value if found."""
    for loader in [
        browser_cookie3.chrome,
        browser_cookie3.firefox,
        browser_cookie3.safari,
        browser_cookie3.edge,
        browser_cookie3.chromium,
    ]:
        try:
            jar = loader(domain_name=_DOMAIN)
            for cookie in jar:
                if cookie.name == _COOKIE_NAME:
                    return cookie.value
        except Exception:
            continue
    return None


async def get_geoguessr_token() -> str:
    """Return the GeoGuessr _ncfa authentication token.

    Reads from the user's installed browser cookie stores. If the cookie
    is not present, opens geoguessr.com/signin in the default browser and
    polls until the cookie appears (login completed).

    Returns:
        The _ncfa cookie value as a string.

    Raises:
        TimeoutError: if login is not completed within 120 seconds.
    """
    token = await asyncio.to_thread(_read_ncfa)
    if token:
        return token

    webbrowser.open(_SIGNIN_URL)

    for _ in range(_TIMEOUT):
        await asyncio.sleep(_POLL_INTERVAL)
        token = await asyncio.to_thread(_read_ncfa)
        if token:
            return token

    raise TimeoutError(f"GeoGuessr login not completed within {_TIMEOUT} seconds")
