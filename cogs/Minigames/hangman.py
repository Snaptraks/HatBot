import asyncio
import pickle

import numpy as np
import discord

from . import emoji


# load the words at import, not instanciation for better performance
with open('cogs/Minigames/hangman_words.pkl', 'rb') as f:
    WORD_LIST = pickle.load(f)


VALID_CHARACTERS = 'abcdefghijklmnopqrstuvwxyz'


HANGMAN_LIMBS = [
    [(1, 0), emoji.Hangman.DIZZY_FACE.value],
    [(1, 1), emoji.Hangman.SHIRT.value],
    [(1, 2), emoji.Hangman.JEANS.value],
    [(0, 1), emoji.Hangman.POINT_LEFT.value],
    [(2, 1), emoji.Hangman.POINT_RIGHT.value],
    [(0, 3), emoji.Hangman.SHOE.value],
    [(2, 3), emoji.Hangman.SHOE.value],
    ]


class Hangman:
    """Class that contains the Hangman game."""

    def __init__(self, ctx, bot):
        self.ctx = ctx
        self.bot = bot
        self.word_to_guess = np.random.choice(WORD_LIST)
        self.chances = 7
        self.won = False
        self.bad_guesses = []
        self.good_guesses = []

        self.embed = discord.Embed(
            title=None,
            type='rich',
            color=np.random.randint(0xFFFFFF),  # Random color
            ).set_author(
            name=self.ctx.author.display_name,
            icon_url=self.ctx.author.avatar_url_as(static_format='png'),
            ).add_field(
            name='Hangman',
            value=None,  # will be filled later
            inline=True,
            ).add_field(
            name='Bad Guesses',
            value=None,
            inline=True,
            ).add_field(
            name='Guess the word!',
            value=None,  # will be filled after
            inline=False,
            )

    async def play(self):
        """Plays a game of Hangman!"""

        def check(message):
            valid = (message.author == self.ctx.author and \
                message.channel == self.ctx.channel) and \
                (len(message.content) == 1 or \
                message.content.lower() == 'cancel')
            return valid

        hint_message = 'Guess the word! Enter a letter to begin.'
        self.update_embed(hint_message)
        self.message_game = await self.ctx.send(embed=self.embed)

        while self.chances > 0 and not self.won:

            guess_message = await self.bot.wait_for('message', check=check)
            guess = guess_message.content.lower()

            if guess.lower() == 'cancel':
                break

            elif guess not in VALID_CHARACTERS:
                hint_message = 'Please enter a single letter'

            elif guess in self.good_guesses + self.bad_guesses:
                hint_message = 'You already tried that one.'

            elif guess not in self.word_to_guess:
                self.chances -= 1
                self.bad_guesses.append(guess)
                hint_message = 'Bad guess! Try another letter.'

            else:
                self.good_guesses.append(guess)
                hint_message = 'Correct! Try another letter.'

            await guess_message.delete()

            self.won = all([x in self.good_guesses
                            for x in set(self.word_to_guess)])

            if not self.won:
                self.update_embed(hint_message)
                await self.message_game.edit(embed=self.embed)

        if self.won:
            hint_message = f'You won! The word was {self.word_to_guess}.'
        else:
            hint_message = f'You lost! The word was {self.word_to_guess}.'

        self.update_embed(hint_message)
        await self.message_game.edit(embed=self.embed)

    def update_embed(self, hint_message):
        """Edits the Embed, the progress on the word to guess, chances,
        and the graphics of the hangman."""

        current_progress = ' '.join(
            emoji.Alphabet[x.upper()].value if x in self.good_guesses
            else emoji.Hangman.BLANK.value for x in self.word_to_guess
            )

        bad_guesses_str = ' '.join(c.upper() for c in self.bad_guesses)
        # if it is an empty string, the Embed will complain
        if not bad_guesses_str:
            bad_guesses_str = None

        graphics = self.make_graphics(len(self.bad_guesses))
        graphics_str = '\n'.join(''.join(line) for line in graphics.T)

        self.embed.set_field_at(
            index=0,  # graphics
            name=self.embed.fields[0].name,
            value=graphics_str,
            inline=self.embed.fields[0].inline,
            ).set_field_at(
            index=1,  # bad guesses
            name=self.embed.fields[1].name,
            value=bad_guesses_str,
            inline=self.embed.fields[1].inline,
            ).set_field_at(
            index=2,  # word to guess
            name=self.embed.fields[2].name,
            value=current_progress,
            inline=self.embed.fields[2].inline,
            ).set_footer(
            text=hint_message,
            )

    def make_graphics(self, number_bad_guesses):
        """Returns an array for the hangman picture with the correct limbs
        displayed according to the number bad guesses made."""

        if number_bad_guesses == 0:
            return np.full((3, 4), emoji.Hangman.BLACK.value)
        else:
            limb = HANGMAN_LIMBS[number_bad_guesses - 1]
            graphics = self.make_graphics(number_bad_guesses - 1)
            graphics[limb[0]] = limb[1]
            return graphics
