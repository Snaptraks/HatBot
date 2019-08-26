import numpy as np

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


class Deck:
    """Class that represents a full deck of cards, consisting of many
    Cards objects. Does not contain Jokers.
    """

    def __init__(self):
        self.cards = [Card(suit, rank)
                      for suit in range(4)
                      for rank in range(1, 14)]

    def __len__(self):
        return len(self.cards)

    def __str__(self):
        return '\n'.join([str(card) for card in self.cards])

    def shuffle(self):
        """Shuffles the cards inplace."""
        np.random.shuffle(self.cards)

    def sort(self):
        """Sorts the cards inplace."""
        self.cards.sort()

    def add_card(self, card):
        """Adds a card to the end of the deck."""
        self.cards.append(card)

    def remove_card(self, card):
        """Removes a given card form the devk."""
        self.cards.remove(card)

    def pop_card(self, *args):
        """Removes and returns a card from the deck,
        the last one by default.
        """
        return self.cards.pop(*args)

    def give_cards(self, hand, amount):
        """Gives the amount of cards from the deck to the player's hand."""
        for i in range(amount):
            hand.add_card(self.pop_card())


class Hand(Deck):
    """Class that represents the hand of a player.
    Inherits most from Deck class.
    """

    def __init__(self):
        self.cards = []

