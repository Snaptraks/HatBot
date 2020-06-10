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


def get_fish_card():
    print('** FISH CARD **')
    with db:
        # get the best catch of the user
        c = db.execute(
            """
            SELECT size, species, catch_time, MAX(weight) as weight
              FROM fishing_fish
             WHERE user_id = :user_id
            """,
            {'user_id': USER_ID}
            )
        best_catch = c.fetchone()

        # get the total experience from fish and interests
        c = db.execute(
            """
            SELECT SUM(amount) AS exp
              FROM (SELECT SUM(weight) AS amount
                      FROM fishing_fish
                     WHERE user_id = :user_id

                     UNION

                    SELECT SUM(amount) AS amount
                      FROM fishing_interest
                     WHERE user_id = :user_id)
            """,
            {'user_id': USER_ID}
            )
        exp = c.fetchone()

        print(Fish(**dict(best_catch)))
        print(dict(exp))
        print()


def get_fish_exptop():
    print('** FISH EXPTOP **')
    with db:
        c = db.execute(
            """
            SELECT user_id, SUM(amount) AS exp
              FROM (SELECT user_id, SUM(weight) AS amount
                      FROM fishing_fish
                     GROUP BY user_id

                     UNION

                    SELECT user_id, SUM(amount) AS amount
                      FROM fishing_interest
                     GROUP BY user_id)
             GROUP BY user_id
             ORDER BY exp DESC
            """
            )

    rows = c.fetchall()
    for row in rows:
        print(dict(row))

    print()


def get_fish_inventory():
    print('** FISH INVENTORY **')
    with db:
        c = db.execute(
            """
            SELECT *
              FROM fishing_fish
             WHERE user_id = :user_id
               AND state = 0
             ORDER BY weight ASC
            """,
            {'user_id': USER_ID}
            )

    rows = c.fetchall()
    print(f'{len(rows)} in inventory')
    for row in rows:
        print(Fish(**dict(row)))

    print()


def get_fish_journal():
    print('** FISH JOURNAL **')
    with db:
        c = db.execute(
            """
            SELECT size, species, COUNT(species) AS number_catch
              FROM fishing_fish
             WHERE user_id = :user_id
             GROUP BY size, species
             ORDER BY weight ASC
            """,
            {'user_id': USER_ID}
            )

    rows = c.fetchall()
    journal = defaultdict(Counter)
    for row in rows:
        journal[row['size']][row['species']] += row['number_catch']
        # print(Fish(**dict(row)), row['number_catch'])
    pprint(journal)

    print()


def get_fish_slap():
    print('** FISH SLAP **')
    with db:
        c = db.execute(
            """
            SELECT *
              FROM fishing_fish
             WHERE user_id = :user_id
               AND state = 0
             ORDER BY RANDOM()
             LIMIT 1
            """,
            {'user_id': USER_ID}
            )

    row = c.fetchone()
    print(dict(row))

    print()


def get_fish_top():
    print('** FISH TOP **')
    with db:
        c = db.execute(
            """
            SELECT size, species, MAX(weight) AS weight, user_id, catch_time
              FROM fishing_fish
             GROUP BY user_id
             ORDER BY weight DESC
            """
            )

    rows = c.fetchall()
    print(f'{len(rows)} entries in Top')
    for row in rows:
        print(Fish(**dict(row)), row['user_id'])

    print()


def get_experience():
    print('** USER EXPERIENCE **')
    with db:
        c = db.execute(
            """
            SELECT SUM(amount) AS exp
              FROM (SELECT SUM(weight) AS amount
                      FROM fishing_fish
                     WHERE user_id = :user_id
                       AND state = 1

                     UNION

                    SELECT SUM(amount) AS amount
                      FROM fishing_interest
                     WHERE user_id = :user_id)
            """,
            {'user_id': USER_ID}
            )

    row = c.fetchone()
    print(f'User has {row["exp"]} exp')
    print()


def get_misc_stats():
    print('** MISC STATS **')
    with db:
        c = db.execute('SELECT * FROM fishing_fish')
        print(f'{len(c.fetchall())} total fish in DB')

        c = db.execute('SELECT * FROM fishing_fish GROUP BY user_id')
        print(f'{len(c.fetchall())} total users in DB')

        for size in FISH_SPECIES.keys():
            c = db.execute('SELECT * FROM fishing_fish WHERE size = ?', (size,))
            print(f'{len(c.fetchall())} {size} fish')

        print()


if __name__ == '__main__':
    get_fish_bomb()
    get_fish_card()
    get_fish_exptop()
    get_fish_inventory()
    get_fish_journal()
    get_fish_slap()
    get_fish_top()
    get_misc_stats()

    get_experience()
