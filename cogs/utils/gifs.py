import config


async def search_gif(http_session, query):
    """Return a gif when searching for a specific query."""
    return await _tenor_endpoint('search', http_session, query)


async def random_gif(http_session, query):
    """Return a random gif related to the query."""
    return await _tenor_endpoint('random', http_session, query)


async def _tenor_endpoint(endpoint, http_session, query):
    """Get a gif from Tenor"""

    query = query.split()
    if len(query) >= 1:
        search_random = (
            f'https://api.tenor.com/v1/{endpoint}?key={config.tenor_api_key}'
            f'&q={query}&limit=1&media_filter=basic&contentfilter=low'
            )
        async with http_session.get(search_random) as resp:
            if resp.status == 200:
                try:
                    json_resp = await resp.json()
                    json_resp = json_resp['results']
                    gif = json_resp[0]
                    gif = gif.get('media')
                    gif = gif[0]
                    gif = gif.get('gif')
                    gif = gif.get('url')
                    return gif
                except Exception as e:
                    pass
    return ''
