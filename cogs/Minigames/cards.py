# from . import emoji

# Inspired by https://github.com/AllenDowney/ThinkPython2


class Card:
    """Class that represents a normal playing card."""

    # TODO: implement emojis
    suit_names = ['Clubs', 'Diamonds', 'Hearts', 'Spades']
    rank_names = [None, 'A', '2', '3', '4', '5', '6', '7',
        '8', '9', '10', 'J', 'Q', 'K']

    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self._card = (suit, rank)

    def __str__(self):
        return f'{self.rank_names[self.rank]} of {self.suit_names[self.suit]}'

    def __eq__(self, other):
        """Use the type tuple to make equality check."""
        return self._card == other._card

    def __lt__(self, other):
        """Use the type tuple to make the comparaison.
        Sorts first by suit, then by rank.
        """
        return self._card < other._card
