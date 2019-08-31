import asyncio
import discord

from cards import Deck, Hand


class Blackjack:
    def __init__(self, ctx, bot):
        self.deck = Deck()
        self.deck.shuffle()

        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.deck.give_cards(self.player_hand, 2)
        self.deck.give_cards(self.dealer_hand, 2)

    async def play(self):
        # display cards?
        while True:
            print('Player:', self.player_hand.cards)
            print('Dealer:', self.dealer_hand.cards[:-1])
            # check for blackjacks
            if self.calculate_score(self.player_hand) == 21:
                print('Player got a Blackjack!')
                return
            elif self.calculate_score(self.dealer_hand) == 21:
                print('Dealer got a Blackjack!')
                return

            # ask player input
            move = input('[H]it or [S]tand? ').upper()
            # if hit
            if move == 'H':
                # give card
                self.deck.give_cards(self.player_hand, 1)
                print(self.player_hand.cards)
                if self.calculate_score(self.player_hand) > 21:
                    print('Player busted.')
                    return
            # elif stand
            elif move == 'S':
                # give dealer card until total is above 17
                while self.calculate_score(self.dealer_hand) < 17:
                    self.deck.give_cards(self.dealer_hand, 1)
                    print(self.dealer_hand.cards)
                    if self.calculate_score(self.dealer_hand) > 21:
                        print('Dealer busted.')
                        return

                if self.calculate_score(self.dealer_hand) > \
                        self.calculate_score(self.player_hand):
                    print('Dealer won.')

                elif self.calculate_score(self.dealer_hand) < \
                        self.calculate_score(self.player_hand):
                    print('Player won.')

                else:
                    print('Tie')

                return

    def calculate_score(self, hand):
        hand = hand.cards.copy()
        hand = sorted(hand, reverse=True)  # put aces at the end
        score = 0
        for card in hand:
            if card.rank > 10:
                score += 10
            elif card.rank == 1:  # an ace
                if score < 11:
                    score += 11
                else:
                    score += 1
            else:
                score += card.rank
        return score

    def update_embed(self):
        pass
