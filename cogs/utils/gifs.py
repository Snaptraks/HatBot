import random
import config


async def random_gif(http_session, query):
    """Return a random gif related to the query."""

    limit = 10
    params = {
        "q": query,
        "limit": limit,
        "pos": limit * random.randint(0, 10),
        "media_filter": "minimal",
        "contentfilter": "high",
        "locale": "en",
    }
    resp = await _tenor_endpoint(http_session, "search", params)
    resp = resp['results']
    random_gif = random.choice(resp)
    gif_url = random_gif['media'][0]['gif']['url']

    return gif_url


async def _tenor_endpoint(http_session, endpoint, params):
    """Get a gif from Tenor"""

    query = params["q"].split()
    params["key"] = config.tenor_api_key
    if len(query) >= 1:
        async with http_session.get(f"https://api.tenor.com/v1/{endpoint}",
                                    params=params) as resp:
            if resp.status == 200:
                try:
                    json_resp = await resp.json()
                    return json_resp
                except Exception:
                    pass
    return ""
