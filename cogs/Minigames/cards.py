import numpy as np

from . import emoji

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
        self.suit_name = self.suit_names[suit]
        self.rank_name = self.rank_names[rank]
        self._card = (suit, rank)

    def __str__(self):
        return f'{self.rank_name} of {self.suit_name}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.suit}, {self.rank})'

    def __eq__(self, other):
        """Use the type tuple to make equality check."""

        return self._card == other._card

    def __lt__(self, other):
        """Use the type tuple to make the comparaison.
        Sorts first by suit, then by rank.
        """
        return self._card < other._card

    @property
    def emoji(self):
        """Return a string of the card's rank and suit, in emoji form."""

        suit = emoji.Suits[self.suit_name.upper()].value
        if self.rank in (1, 11, 12, 13):
            rank = emoji.Alphabet[self.rank_name].value
        else:
            rank = emoji.Numbers[f'_{self.rank}'].value

        return rank + suit


class Deck:
    """Class that represents a full deck of cards, consisting of many
    Cards objects. Does not contain Jokers.
    """

    def __init__(self, cards=None):
        if cards is None:
            self.cards = [Card(suit, rank)
                          for suit in range(4)
                          for rank in range(1, 14)]
        else:
            self.cards = cards

    def __mul__(self, other):
        if isinstance(other, int):
            return self.__class__(cards=self.cards * other)
        else:
            raise ValueError('Invalid types for multiplication.')

    __rmul__ = __mul__

    def __len__(self):
        return len(self.cards)

    def __str__(self):
        return '\n'.join([str(card) for card in self.cards])

    def __iter__(self):
        return iter(self.cards)

    def __next__(self):
        return next(self.cards)

    def shuffle(self):
        """Shuffle the cards inplace."""

        np.random.shuffle(self.cards)

    def sort(self):
        """Sort the cards inplace."""

        self.cards.sort()

    def split(self, parts):
        """Split the deck in n parts."""

        cards_array = np.asarray(self.cards)
        split = np.array_split(cards_array, parts)
        decks = []
        for part in split:
            decks.append(self.__class__(cards=list(part)))

        return decks

    def add_card(self, card):
        """Add a card to the end of the deck."""

        self.cards.append(card)

    def remove_card(self, card):
        """Remove a given card form the deck."""

        self.cards.remove(card)

    def pop_card(self, *args):
        """Remove and return a card from the deck,
        the last one by default.
        """
        return self.cards.pop(*args)

    def give_cards(self, hand, amount):
        """Give the amount of cards from the deck to the player's hand."""
        
        for i in range(amount):
            hand.add_card(self.pop_card())


class Hand(Deck):
    """Class that represents the hand of a player.
    Inherits most from Deck class.
    """

    def __init__(self):
        self.cards = []
