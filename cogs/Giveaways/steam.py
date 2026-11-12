import re


def get_steam_id_from_url(url: str) -> int:
    """Extract the app ID from a Steam page URL.

    Parameters
    ----------
    url : str
        The URL of the game's Steam page.

    Returns
    -------
    int
        The app ID of the game.

    Raises
    ------
    ValueError
        The provided URL is not from Steam.

    """
    match = re.match(r"^https://store.steampowered.com/app/(\d+)/.*?/$", url)
    if not match:
        msg = "Not a Steam URL."
        raise ValueError(msg)

    return int(match.group(1))


async def get_header_from_steam_url(url: str) -> str:
    """Return the URL for the header image of the provided Steam game.

    Parameters
    ----------
    url : str
        The URL of the game's Steam page.

    Returns
    -------
    str
        The URL of the game's header image.

    """
    try:
        steam_id = get_steam_id_from_url(url)
    except ValueError:
        # empty image
        steam_id = 0

    return f"https://cdn.akamai.steamstatic.com/steam/apps/{steam_id}/header.jpg"
