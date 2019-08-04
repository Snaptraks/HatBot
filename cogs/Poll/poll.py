import discord
from discord.ext import commands
import asyncio
import matplotlib.pyplot as plt
import numpy as np
import json
import aiohttp

from ..utils.cog import BasicCog


class Poll(BasicCog):
    def __init__(self, bot):
        super().__init__(bot)

        # https://en.wikipedia.org/wiki/Regional_Indicator_Symbol#Unicode_block
        self.emojiLetters = [chr(i) for i in range(0x1F1E6, 0x1F200)]

        self.http_session = aiohttp.ClientSession()

    def cog_unload(self):
        super().cog_unload()
        self.bot.loop.create_task(self.http_session.close())

    @commands.command()
    async def poll(self, ctx):
        """Creates a poll where users can react to vote.
        Syntax is `!poll {question} [choice 1] [choice 2] +duration hh:mm +keep`
        """
        messageContent = ctx.message.content
        message = ctx.message
        channel = ctx.message.channel
        if messageContent.find("{") == -1:
            await message.add_reaction('\U0001F44D')  # thumbsup
            await message.add_reaction('\U0001F44E')  # thumbsdown
            await message.add_reaction('\U0001F937')  # shrug
        else:
            first = messageContent.find("{") + 1
            second = messageContent.find("}")
            title = messageContent[first:second]

            # gets the # of options and assigns them to an array
            newMessage = messageContent[second:]
            loopTime = 0

            option = []
            for options in messageContent:
                # get from } [option 1]
                # if newThis == -1:
                stillOptions = newMessage.find("[")
                if stillOptions != -1:
                    if loopTime == 0:
                        first = newMessage.find("[") + 1
                        second = newMessage.find("]")
                        second1 = second + 1
                        option.append(newMessage[first:second])
                        loopTime += 1
                    else:
                        newMessage = newMessage[second1:]
                        first = newMessage.find("[") + 1
                        second = newMessage.find("]")
                        second1 = second + 1
                        option.append(newMessage[first:second])
                        loopTime += 1

            try:
                pollMessage = ""

                # there is probably a better way to do this
                i = 0
                for choice in option:
                    if not option[i] == "":
                        if len(option) > 21:
                            await message.channel.send("Maximum of 20 options")
                            return
                        elif not i == len(option) - 1:
                            pollMessage = pollMessage + "\n\n" + \
                                self.emojiLetters[i] + " " + choice
                    i += 1

                e = discord.Embed(
                    title="**" +
                    title +
                    "**",
                    description=pollMessage +
                    "\n\n[Support the development of Poll Bot](github.com/finnreid19/poll-bot)",
                    colour=0x83bae3)
                pollMessage = await message.channel.send(embed=e)
                i = 0
                final_options = []  # There is a better way to do this for sure, but it also works that way
                for choice in option:
                    if not i == len(option) - 1 and not option[i] == "":
                        final_options.append(choice)
                        await pollMessage.add_reaction(self.emojiLetters[i])
                    i += 1

                if '+duration' in message.content:
                    messageWords = message.content.split(' ')
                    for i in messageWords:
                        if i == '+duration':
                            time = messageWords[messageWords.index(i) + 1]
                    time = time.split(':')
                    timeSeconds = int(time[0]) * 60 * 60 + int(time[1]) * 60
                    await asyncio.sleep(timeSeconds)
                    pollMessage = await pollMessage.channel.fetch_message(pollMessage.id)
                    reactions = []
                    for reaction in pollMessage.reactions:
                        if reaction.me and reaction.emoji in self.emojiLetters:
                            reactions.append(reaction.count - 1)
                    print(reactions)
                    plt.subplots(figsize=(9, 6))
                    plt.pie(
                        reactions,
                        labels=None,
                        startangle=90,
                        shadow=True,
                        counterclock=False,
                        autopct=lambda pct: form(
                            pct,
                            reactions))
                    plt.title(title, fontsize=27)
                    plt.axis('equal')
                    plt.legend(labels=final_options, loc='lower right')
                    plt.savefig('cogs/Poll/results.png')
                    await message.channel.send('Results for a passed poll',
                                               file=discord.File('cogs/Poll/results.png'))
                    if '+keep' not in message.content:
                        await pollMessage.delete()

            except KeyError:
                return "Please make sure you are using the format 'poll {title} [Option1] [Option2] [Option 3]'"

    @commands.command()
    async def strawpoll(self, ctx):
        """Creates a strawpoll poll, and shares the link.
        Syntax is `!strawpoll {question} [choice 1] [choice 2]`
        """
        message = ctx.message.content

        # gets the title of the poll
        first = message.find("{") + 1
        second = message.find("}")
        title = message[first:second]

        # gets the # of options and assigns them to an array
        newMessage = message[second:]
        loopTime = 0

        option = []
        for options in message:
            # get from } [option 1]
            # if newThis == -1:
            stillOptions = newMessage.find("[")
            if stillOptions != -1:
                if loopTime == 0:
                    first = newMessage.find("[") + 1

                    second = newMessage.find("]")
                    second1 = second + 1
                    option.append(newMessage[first:second])

                    loopTime += 1
                else:
                    newMessage = newMessage[second1:]
                    first = newMessage.find("[") + 1
                    second = newMessage.find("]")
                    second1 = second + 1
                    option.append(newMessage[first:second])
                    loopTime += 1

        try:
            data = {"title": title,
                    "options": option[:(len(option) - 1)],
                    "multi": "false"}
            async with self.http_session.post(
                    'https://www.strawpoll.me/api/v2/polls',
                    data=json.dumps(data),
                    headers={"Content Type": "application/json"}) as resp:
                rjson = await resp.json()
                await ctx.send("https://strawpoll.me/" + str(rjson["id"]))

        except discord.errors.HTTPException:
            return "Please make sure you are using the format 'strawpoll {title} [Option1] [Option2] [Option 3]'"

        except KeyError:
            return "Please make sure you are using the format 'strawpoll {title} [Option1] [Option2] [Option 3]'"


def form(pct, allvals):
    absolute = int(pct / 100. * np.sum(allvals))
    if absolute == 0:
        return ''
    else:
        return "{:.1f}%\n({:d})".format(pct, absolute)
