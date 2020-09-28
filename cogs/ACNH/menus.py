from datetime import datetime

import discord
from discord.ext import menus

from . import objects


def make_profile_embed(member, profile_data, thumbnail_url):
    """Return the discord.Embed for the AC:NH profile card."""

    try:
        hemisphere = objects.PROFILE_HEMISPHERE[
            profile_data['hemisphere']].title()
    except TypeError:
        hemisphere = None

    try:
        fruit = profile_data['native_fruit']
        native_fruit = (
            f"{objects.PROFILE_FRUIT[fruit].title()} "
            f"{objects.PROFILE_FRUIT_EMOJI[fruit]}"
        )
    except TypeError:
        native_fruit = None

    embed = discord.Embed(
        title="Animal Crossing: New Horizons Profile Card",
        color=objects.PROFILE_EMBED_COLOR,
        timestamp=datetime.utcnow(),
    ).set_author(
        name=member.display_name,
        icon_url=member.avatar_url,
    ).set_thumbnail(
        url=thumbnail_url,
    ).add_field(
        name="Resident Name",
        value=profile_data['resident_name'],
    ).add_field(
        name="Island Name",
        value=profile_data['island_name'],
    ).add_field(
        name="Hemisphere",
        value=hemisphere,
    ).add_field(
        name="Native Fruit",
        value=native_fruit,
    ).add_field(
        name="Friend Code",
        value=profile_data['friend_code'],
    ).add_field(
        name="Creator ID",
        value=profile_data['creator_id'],
    ).add_field(
        name="Dream Address",
        value=profile_data['dream_address'],
    )

    return embed


class ProfileSource(menus.ListPageSource):
    """Page source to format the profile menu."""

    def __init__(self, entries):
        super().__init__(entries, per_page=1)

    async def format_page(self, menu, page):
        thumbnail_url = objects.PROFILE_DEFAULT_THUMBNAIL
        member_id = page['user_id']
        member = menu.ctx.guild.get_member(member_id)

        return make_profile_embed(member, page, thumbnail_url)
