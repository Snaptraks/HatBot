from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import TYPE_CHECKING

import discord
import tomllib
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from snapcogs.bot import Bot


LOGGER = logging.getLogger(__name__)
PATH = Path(__file__).parent

# We do not care about the year of the event (they repeat every year)
# But we chose a leap year, to allow for February 29 as a valid date.
YEAR = 2020

# Format used to parse dates
DATE_FMT = "%B %d %Y"


class EventCache:
    """Class that encapsulates the handling of the event caching."""

    path = PATH / "event_cache.txt"

    @classmethod
    def set_cache(cls, event: str) -> None:
        """Save the current event name to disk."""

        with open(cls.path, "w") as f:
            f.write(event)

    @classmethod
    def get_cache(cls) -> str | None:
        """Read the last event name from disk if it exists, else return None."""

        if cls.path.exists():
            with open(cls.path, "r") as f:
                return f.read()
        else:
            return None


@dataclass
class Event:
    """Dataclass containing the pertinent information of an Event."""

    name: str
    file_name: str
    start_date: date | None = None
    end_date: date | None = None
    fallback: bool = False


def parse_events(config_raw: bytes) -> list[Event]:
    """Parse the raw bytes of the config.toml file in the HatBot-Avatar repository.
    Return a list of Events, with the appropriate values converted to rich types,
    like datetime.date.
    """

    events_raw = tomllib.loads(config_raw.decode())
    events = []

    for name, data in events_raw.items():
        for bound in ("start_date", "end_date"):
            if (d := data.get(bound)) is not None:
                events_raw[name][bound] = (
                    datetime.strptime(f"{d} {YEAR}", DATE_FMT)
                    .replace(tzinfo=UTC)
                    .date()
                )
        event = Event(name=name, **data)
        if not event.fallback and None in (event.start_date, event.end_date):
            raise RuntimeError(
                "Non-fallback event needs start_date and end_date configured"
            )
        events.append(event)

    return events


class AvatarRepository:
    """Class that handles fetching the assets from the repository."""

    base_url = "https://raw.githubusercontent.com/Snaptraks/HatBot-Avatar/main"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def get_current_event(self) -> Event | None:
        """Get the event from the present date and return the attached data.
        If no special event was found, return the fallback one (default avatar).
        """
        events = parse_events(await self.fetch_events_config())
        now = discord.utils.utcnow()
        lookup_date = date(year=YEAR, month=now.month, day=now.day)
        LOGGER.debug(f"Looking for event at {lookup_date}.")

        for event in events:
            # we ignore type checking here because if the dates are None and fallback
            # is False, it will raise an error in parse_events anyway
            if not event.fallback and (
                event.start_date <= lookup_date <= event.end_date  # type: ignore
            ):
                LOGGER.debug(f"Found event {event.name}.")
                return event

        LOGGER.debug("No active event was found, looking for fallback event.")

        for event in events:
            if event.fallback:
                LOGGER.debug("Found fallback event.")
                return event

        LOGGER.warning("No active event and no fallback found!")
        return None

    async def fetch_events_config(self) -> bytes:
        """Get the raw data from the config.toml file in the repository."""

        config_url = f"{self.base_url}/config.toml"
        LOGGER.debug("Fetching events config.")
        return await self.fetch_file(config_url)

    async def fetch_event_avatar(self, event: Event) -> bytes:
        """Get the event avatar file from the repository."""

        avatar_url = f"{self.base_url}/{event.name}/{event.file_name}"
        LOGGER.debug(f"Fetching {event.name} avatar.")
        return await self.fetch_file(avatar_url)

    async def fetch_file(self, download_url: str) -> bytes:
        """Abstract downloading a file from the repository.
        Get the file from the given URL and return the raw bytes.
        It might raise an exception in the case of an incorrect URL.
        """

        LOGGER.debug(f"Fetching {download_url}")
        async with self.bot.http_session.get(download_url) as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to fetch file (status {response.status}).")

            LOGGER.debug("Fetched successfully.")
            return await response.read()


class Avatar(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.repository = AvatarRepository(bot)
        self.event_avatars.start()

    @tasks.loop(time=time(hour=0, minute=1, tzinfo=UTC))
    async def event_avatars(self) -> None:
        """Task to check if we have entered a new event, and possibly change
        the bot's avatar.
        """

        event = await self.repository.get_current_event()
        if event is None:
            LOGGER.warning("No event found. Maybe the config file is wrong?")
            return

        if event.name != EventCache.get_cache():
            LOGGER.info(f"New event detected! Changing avatar for {event.name}...")
            EventCache.set_cache(event.name)
            await self.edit_avatar(event)

    @event_avatars.before_loop
    async def event_avatars_before(self) -> None:
        """Call the event_avatars task once immediately to make sure the
        avatar is up to date.
        """
        await self.bot.wait_until_ready()
        LOGGER.debug("Running event_avatars once at startup.")
        await self.event_avatars()

    async def edit_avatar(self, event: Event) -> None:
        """Fetch the event's avatar from the repository and edit the bot's avatar."""

        avatar = await self.repository.fetch_event_avatar(event)
        # we ignore type here since we will always try to edit the avatar
        # only if the bot is logged in (self.bot.user is not None)
        await self.bot.user.edit(avatar=avatar)  # type: ignore
        LOGGER.debug(f"Successfully edited the bot's avatar for {event.name}.")

    @commands.command()
    @commands.is_owner()
    async def avatar_refresh(self, ctx: commands.Context) -> None:
        """Refresh the bot's current avatar by fetching it from the repository."""

        event = await self.repository.get_current_event()
        if event is None:
            LOGGER.warning("No event found. Maybe the config file is wrong?")
            await ctx.message.add_reaction("\N{CROSS MARK}")
            return

        LOGGER.debug(f"Manually changing the bot's avatar for {event.name}.")
        await self.edit_avatar(event)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
