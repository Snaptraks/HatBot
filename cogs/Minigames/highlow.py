import asyncio
import discord

from cards import Deck, Hand


class HighLow:
    def __init__(self):
        self.deck = Deck()
        self.deck.shuffle()
        # use half a deck since it can be a long game otherwise
        self.deck = self.deck.split(2)[0]
        self.dealer_score = 0
        self.player_score = 0

    def play(self):
        dstr = {'H': 'higher', 'L': 'lower'}
        prev_card = self.deck.pop_card()
        while len(self.deck) > 0:
            card = self.deck.pop_card()
            print(prev_card)
            guess = input('Higher or Lower? ').upper()
            if (guess == 'H' and prev_card.rank < card.rank) or \
                    (guess == 'L' and card.rank < prev_card.rank):
                print(f'Yep! {card} is {dstr[guess]} than {prev_card}')
                self.player_score += 1

            elif prev_card.rank == card.rank:
                print('Actually, that was mean.')

            else:
                print('Nope!')
                self.dealer_score += 1

            prev_card = card

        print('No more cards!')
        print(f'Dealer: {self.dealer_score}\nPlayer: {self.player_score}')


if __name__ == '__main__':
    game = HighLow()
    game.play()
