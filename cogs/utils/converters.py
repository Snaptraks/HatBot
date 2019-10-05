import re
from datetime import datetime, timedelta

from discord.ext.commands import BadArgument, Context, Converter

def build_duration(**kwargs):
    """Converts a dict with the keys defined in `Duration` to a timedelta
    object. Here we assume a month is 30 days, and a year is 365 days.
    """
    weeks = kwargs.get('weeks', 0)
    days = 365 * kwargs.get('years', 0) \
        + 30 * kwargs.get('months', 0) \
        + kwargs.get('days')
    hours = kwargs.get('hours', 0)
    minutes = kwargs.get('minutes', 0)
    seconds = kwargs.get('seconds', 0)

    return timedelta(
        days=days,
        seconds=seconds,
        minutes=minutes,
        hours=hours,
        weeks=weeks,
        )


class Duration(Converter):
    """Convert duration strings into UTC datetime.datetime objects.
    Inspired by the https://github.com/python-discord/bot repository.
    """

    duration_parser = re.compile(
        r"((?P<years>\d+?) ?(years|year|Y|y) ?)?"
        r"((?P<months>\d+?) ?(months|month|M) ?)?"  # switched m to M
        r"((?P<weeks>\d+?) ?(weeks|week|W|w) ?)?"
        r"((?P<days>\d+?) ?(days|day|D|d) ?)?"
        r"((?P<hours>\d+?) ?(hours|hour|H|h) ?)?"
        r"((?P<minutes>\d+?) ?(minutes|minute|min|m) ?)?"  # switched M to m
        r"((?P<seconds>\d+?) ?(seconds|second|S|s))?"
    )

    async def convert(self, ctx: Context, duration: str) -> datetime:
        """
        Converts a `duration` string to a timedelta object that's
        `duration` long.

        The converter supports the following symbols for each unit of time:
        - years: `Y`, `y`, `year`, `years`
        - months: `m`, `month`, `months`
        - weeks: `w`, `W`, `week`, `weeks`
        - days: `d`, `D`, `day`, `days`
        - hours: `H`, `h`, `hour`, `hours`
        - minutes: `m`, `minute`, `minutes`, `min`
        - seconds: `S`, `s`, `second`, `seconds`

        The units need to be provided in **descending** order of magnitude.
        """
        match = self.duration_parser.fullmatch(duration)
        if not match:
            raise BadArgument(f"`{duration}` is not a valid duration string.")

        duration_dict = {unit: int(amount) \
            for unit, amount in match.groupdict(default=0).items()}
        delta = build_duration(**duration_dict)

        return delta
