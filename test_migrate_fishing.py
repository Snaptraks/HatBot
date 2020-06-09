from collections import defaultdict, Counter
import sqlite3
import json
import pickle
from pprint import pprint


with open('cogs/Fishing/fish.json') as f:
    FISH_SPECIES = json.load(f)


class Fish:
    """Temp class to better print the fish."""
    def __init__(self, **kwargs):
        self.size = kwargs.get('size')
        species_index = kwargs.get('species')
        self.smell = kwargs.get('smell')
        self.weight = kwargs.get('weight', 0)
        self.user_id = kwargs.get('user_id')
        self.catch_time = kwargs.get('catch_time')

        self.species = FISH_SPECIES[self.size]['species'][species_index]

    def __repr__(self):
        return (
            f'{self.size.title()} {self.species} ({self.weight:.3f} kg)\n'
            f'[{self.catch_time}]'
            )


db = sqlite3.connect('HatBot.db')
db.row_factory = sqlite3.Row
USER_ID = 337266376941240320


with db:
    c = db.execute('SELECT * FROM fishing_fish')
    print(f'{len(c.fetchall())} total fish in DB')
def get_fish_bomb():
    print('** FISH BOMB **')
    with db:
        c = db.execute(
            """
            SELECT *
              FROM fishing_fish
             WHERE user_id = :user_id
               AND state = 0
             ORDER BY weight DESC
             LIMIT 10
            """,
            {'user_id': USER_ID}
            )
    rows = c.fetchall()
    print(f'Bombed with {len(rows)} fish')
    for row in rows:
        print(Fish(**dict(row)))

    print()



    c = db.execute('SELECT * FROM fishing_fish GROUP BY user_id')
    print(f'{len(c.fetchall())} total users in DB')

    for size in FISH_SPECIES.keys():
        c = db.execute('SELECT * FROM fishing_fish WHERE size = ?', (size,))
        print(f'{len(c.fetchall())} {size} fish')

    c = db.execute('SELECT * FROM fishing_fish WHERE user_id = 337266376941240320')
    print(len(c.fetchall()))
    print(fish_data[337266376941240320]['total_caught'])
if __name__ == '__main__':
    get_fish_bomb()
