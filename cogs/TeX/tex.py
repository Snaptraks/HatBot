import asyncio
import os
import re
import sys
import time

import discord
from discord.ext import commands
from discord.ext import tasks

from ..utils.cogs import BasicCog


with open('cogs/TeX/struct.tex', 'r') as f:
    LATEX_FILE = ''.join(f.readlines())


LATEX_TEMP_PATH = 'cogs/TeX/temp/'


def get_latex_cmds(tempfile):
    cmds = [
        [  # pdflatex compilation in temporary folder
            'pdflatex',
            '-synctex=1',
            '-interaction=nonstopmode',
            '-file-line-error',
            '-output-directory',
            LATEX_TEMP_PATH,
            f'{LATEX_TEMP_PATH}{tempfile}.tex',
            ],
        [  # pdf to png convert
            'pdftoppm',
            '-png',
            f'{LATEX_TEMP_PATH}{tempfile}.pdf',
            f'{LATEX_TEMP_PATH}{tempfile}',
            ],
        ]

    return cmds


class TeX(BasicCog):
    """Cog to display valid TeX equations.
    Parse messages looking for equation blocks, compile them and send
    the resulting equation back.
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.clean_temp_folder.start(expiration=24 * 3600)

    def cog_unload(self):
        self.clean_temp_folder.cancel()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Parse the message to check if there is a valid LaTeX equation."""

        matches = re.findall(r'\$.*?(?<!\\\\)\$', message.content)

        for i, match in enumerate(matches):
            tempfile = f'{message.id}_{i}'
            with open(f'{LATEX_TEMP_PATH}{tempfile}.tex', 'w') as f:
                f.write(LATEX_FILE.replace('%equation%', match.strip('$')))

            for cmd in get_latex_cmds(tempfile):
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    )
                await process.wait()

            file = discord.File(f'{LATEX_TEMP_PATH}{tempfile}-1.png')
            await message.channel.send(file=file)

    @tasks.loop(hours=1)
    async def clean_temp_folder(self, expiration):
        """Clean temporary files if they are older than 'expiration'
        seconds.
        """
        for file in os.listdir(LATEX_TEMP_PATH):
            file_path = os.path.join(LATEX_TEMP_PATH, file)
            if (time.time() - os.path.getmtime(file_path)) > expiration:
                os.remove(file_path)
