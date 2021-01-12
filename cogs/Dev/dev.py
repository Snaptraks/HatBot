import asyncio
from contextlib import redirect_stdout
import datetime
import inspect
import io
import re
import subprocess
import unicodedata
import textwrap
import traceback

import discord
from discord.ext import commands, menus

from ..utils.cogs import BasicCog
from ..utils.menus import ShellOutputSource, format_shell_output

# Some commands taken from
# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py


class Dev(BasicCog):
    """Owner only commands to test code."""

    def __init__(self, bot):
        super().__init__(bot)
        self._last_result = None

    def cleanup_code(self, content):
        """Automatically remove code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    async def run_process(self, command):
        """From
        https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py
        """

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            result = await self.bot.loop.run_in_executor(
                None, process.communicate)

        return [output.decode('utf-8', 'ignore') for output in result]

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    def get_syntax_error(self, e):
        if e.text is None:
            return f"```py\n{e.__class__.__name__}: {e}\n```"
        return (
            f"```py\n{e.text}{'^':>{e.offset}}\n"
            f"{e.__class__.__name__}: {e}```"
        )

    @commands.command(name='eval')
    async def _eval(self, ctx, *, body: str):
        """Evaluate a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        if not re.search(  # Check if it's an expression
                r"^(return|import|for|while|def|class|"
                r"from|exit|[a-zA-Z0-9]+\s*=)", body, re.M) \
                and len(body.split("\n")) == 1:
            body = f"return {body}"

        stdout = io.StringIO()

        to_compile = f"async def func():\n{textwrap.indent(body, '  ')}"

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.reply(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.reply(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except BaseException:
                pass

            if ret is None:
                if value:
                    await ctx.reply(f"```py\n{value}\n```")
            else:
                self._last_result = ret
                await ctx.reply(f"```py\n{value}{ret}\n```")

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.channel)
    async def repl(self, ctx):
        """Launch an interactive REPL session."""

        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': ctx.message,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'author': ctx.author,
            '_': None,
        }

        await ctx.reply(
            "Enter code to execute or evaluate. "
            "`exit()` or `quit` to exit."
        )

        def check(m):
            return m.author.id == ctx.author.id and \
                m.channel.id == ctx.channel.id and \
                m.content.startswith("`")

        while True:
            try:
                response = await self.bot.wait_for(
                    'message',
                    check=check,
                    timeout=10.0 * 60.0
                )
            except asyncio.TimeoutError:
                await ctx.reply("Exiting REPL session.")
                break

            cleaned = self.cleanup_code(response.content)

            if cleaned in ("quit", "exit", "exit()"):
                await response.reply("Exiting.")
                return None

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, "<repl session>", "eval")
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, "<repl session>", "exec")
                except SyntaxError as e:
                    await response.reply(self.get_syntax_error(e))
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception:
                value = stdout.getvalue()
                fmt = f"```py\n{value}{traceback.format_exc()}\n```"
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = f"```py\n{value}{result}\n```"
                    variables['_'] = result
                elif value:
                    fmt = f"```py\n{value}\n```"

            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await response.reply("Content too big to be printed.")
                    else:
                        await response.reply(fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await response.reply(f"Unexpected error: `{e}`")

    @repl.error
    async def repl_error(self, ctx, error):
        """Error hangling for the repl command."""

        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.reply(
                "Already running a REPL session. "
                "Exit it with `exit` or `quit`."
            )

        else:
            raise error

    @commands.command()
    async def sh(self, ctx, *, command):
        """Runs a shell command."""

        async with ctx.typing():
            stdout, stderr = await self.run_process(command)

        paginator = format_shell_output(stdout, stderr)

        menu = menus.MenuPages(
            source=ShellOutputSource(paginator.pages),
            clear_reactions_after=True,
        )

        await menu.start(ctx)

    @commands.command()
    async def charinfo(self, ctx, *, characters):
        """Shows you information on up to 25 unicode characters.
        Adapted from
        https://github.com/python-discord/bot/blob/master/bot/cogs/utils.py
        """
        match = re.match(r"<(a?):(\w+):(\d+)>", characters)
        if match:
            embed = discord.Embed(
                title="Non-Character Detected",
                description=(
                    "Only unicode characters can be processed, but a custom "
                    "Discord emoji was found. Please remove it and try again."
                )
            )
            embed.colour = discord.Colour.red()
            await ctx.reply(embed=embed)
            return

        if len(characters) > 25:
            embed = discord.Embed(
                title=f"Too many characters ({len(characters)}/25)",
                colour=discord.Colour.red(),
            )

            await ctx.reply(embed=embed)
            return

        def get_info(char):
            digit = f"{ord(char):x}"
            if len(digit) <= 4:
                u_code = f"\\u{digit:>04}"
            else:
                u_code = f"\\U{digit:>08}"
            url = f"https://www.compart.com/en/unicode/U+{digit:>04}"
            name = f"[{unicodedata.name(char, '')}]({url})"
            info = f"`{u_code.ljust(10)}`: {name} - {char}"
            return info, u_code

        charlist, rawlist = zip(*(get_info(c) for c in characters))

        embed = discord.Embed(description="\n".join(charlist))
        embed.set_author(name="Character Info")

        if len(characters) > 1:
            embed.add_field(
                name="Raw",
                value=f"`{''.join(rawlist)}`",
                inline=False,
            )

        await ctx.reply(embed=embed)
