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
        self.owner_id = kwargs.get('owner_id')
        self.catch_time = kwargs.get('catch_time')
        self.caught_by = kwargs.get('caught_by')

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
             WHERE owner_id = :owner_id
               AND state = 0
             ORDER BY weight DESC
             LIMIT 10
            """,
            {'owner_id': USER_ID}
            )
    rows = c.fetchall()
    print(f'Bombed with {len(rows)} fish')
    for row in rows:
        print(Fish(**row))

    print()


def get_fish_card():
    print('** FISH CARD **')
    with db:
        # get the best catch of the user
        c = db.execute(
            """
            SELECT size, species, catch_time, MAX(weight) as weight
              FROM fishing_fish
             WHERE caught_by = :caught_by
            """,
            {'caught_by': USER_ID}
            )
        best_catch = c.fetchone()
        print(dict(best_catch))

        # get the total experience from fish and interests
        c = db.execute(
            """
            SELECT SUM(amount) AS exp
              FROM (SELECT SUM(weight) AS amount
                      FROM fishing_fish
                     WHERE owner_id = :member_id

                     UNION

                    SELECT SUM(amount) AS amount
                      FROM fishing_interest
                     WHERE user_id = :member_id)
            """,
            {'member_id': USER_ID}
            )
        exp = c.fetchone()

        print(Fish(**best_catch))
        print(dict(exp))
        print()


def get_fish_exptop():
    print('** FISH EXPTOP **')
    with db:
        c = db.execute(
            """
            SELECT id, SUM(amount) AS exp
              FROM (SELECT owner_id AS id, SUM(weight) AS amount
                      FROM fishing_fish
                     WHERE state = 1
                     GROUP BY id

                     UNION

                    SELECT user_id AS id, SUM(amount) AS amount
                      FROM fishing_interest
                     GROUP BY id)
             GROUP BY id
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
             WHERE owner_id = :owner_id
               AND state = 0
             ORDER BY weight ASC
            """,
            {'owner_id': USER_ID}
            )

    rows = c.fetchall()
    print(f'{len(rows)} in inventory')
    for row in rows:
        print(Fish(**row))

    print()


def get_fish_journal():
    print('** FISH JOURNAL **')
    with db:
        c = db.execute(
            """
            SELECT size, species, COUNT(species) AS number_catch
              FROM fishing_fish
             WHERE caught_by = :caught_by
             GROUP BY size, species
             ORDER BY weight ASC
            """,
            {'caught_by': USER_ID}
            )

    rows = c.fetchall()
    journal = defaultdict(Counter)
    for row in rows:
        journal[row['size']][row['species']] += row['number_catch']
        # print(Fish(**row), row['number_catch'])
    pprint(journal)

    print()


def get_fish_slap():
    print('** FISH SLAP **')
    with db:
        c = db.execute(
            """
            SELECT *
              FROM fishing_fish
             WHERE owner_id = :owner_id
               AND state = 0
             ORDER BY RANDOM()
             LIMIT 1
            """,
            {'owner_id': USER_ID}
            )

    row = c.fetchone()
    print(dict(row))

    print()


def get_fish_top():
    print('** FISH TOP **')
    with db:
        c = db.execute(
            """
            SELECT size, species, MAX(weight) AS weight, caught_by, catch_time
              FROM fishing_fish
             GROUP BY caught_by
             ORDER BY weight DESC
            """
            )

    rows = c.fetchall()
    print(f'{len(rows)} entries in Top')
    for row in rows:
        print(Fish(**row), row['caught_by'])

    print()


def get_experience():
    print('** USER EXPERIENCE **')
    with db:
        c = db.execute(
            """
            SELECT SUM(amount) AS exp
              FROM (SELECT SUM(weight) AS amount
                      FROM fishing_fish
                     WHERE owner_id = :owner_id
                       AND state = 1

                     UNION

                    SELECT SUM(amount) AS amount
                      FROM fishing_interest
                     WHERE user_id = :user_id)
            """,
            {'user_id': USER_ID, 'owner_id': USER_ID}
            )

    row = c.fetchone()
    print(f'User has {row["exp"]} exp')
    print()


def get_misc_stats():
    print('** MISC STATS **')
    with db:
        c = db.execute('SELECT * FROM fishing_fish GROUP BY owner_id')
        print(f'{len(c.fetchall())} total users in DB')

        c = db.execute('SELECT * FROM fishing_fish')
        print(f'{len(c.fetchall())} total fish in DB')

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
