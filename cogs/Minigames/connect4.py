import numpy as np


class Board:
    def __init__(self, size_x, size_y):
        self.size_x = size_x
        self.size_y = size_y

        self.board = np.zeros((size_x, size_y), dtype=int)

    def player_play(self, player, column):
        """Adds a player token (1 or 2) to the requested column."""
        pass

    def __repr__(self):
        """Represents the board visually, for debug purposes."""
        rep = '\n'.join(str(line) for line in self.board.T)
        return rep


class Connect4:
    """Class that contains the Connect-4 game."""

    def __init__(self, ctx, bot):
        self.ctx = ctx
        self.bot = bot

    async def play(self):
        pass

    def update_embed(self):
        pass

    def make_graphics(self):
        pass


if __name__ == '__main__':
    board = Board(7, 6)
    print(board)
