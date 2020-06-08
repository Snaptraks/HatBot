"""This file needs to be at the root of the project due to how fish.pkl
is saved.
"""

import sqlite3
import pickle
import json
from pprint import pprint as print  #  so it's easier to print dicts
import datetime

import numpy as np
from scipy.optimize import Bounds, differential_evolution

from cogs.Fishing.fishing import SMELLS


def fix_DT(t):
    """Because I'm stupid and created my own datetime subclass >_>"""
    return datetime.datetime.fromisoformat(t.isoformat())


def insert_fish(c, fish_dict):
    c.execute(
        """
        INSERT INTO fishing_fish
        VALUES (:catch_time,
                :size,
                :smell,
                :species,
                :state,
                :user_id,
                :weight)
        """,
        fish_dict
        )


with open('cogs/Fishing/fish.json') as f:
    FISH_SPECIES = json.load(f)


# db = sqlite3.connect(':memory:')
db = sqlite3.connect('HatBot.db')
db.row_factory = sqlite3.Row
uid = None
# uid = 337266376941240320  # Snaptraks
# uid = 239215575576870914  # xplio
# uid = 167744966431342592  # vashts
# uid = 108010757685248000  # Princerbang
# uid = 309450325050523658  # honkyconky
# uid = 176959813509578752  # goats
# uid = 254730830386167808  # TimTam

# uid = 178613655460380673  # problem

with open('cogs/Fishing/fish_data.pkl', 'rb') as f:
    fish_data = pickle.load(f)
    if uid:
        fish_data = {uid: fish_data[uid]}

# print(fish_data)
# print(fish_data[uid].keys())
# print(sum([e['total_caught'] for e in fish_data.values()]))

with db:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS fishing_fish(
            catch_time TIMESTAMP NOT NULL,
            size       TEXT      NOT NULL,
            smell      INTEGER   NOT NULL,
            species    INTEGER   NOT NULL,
            state      INTEGER   NOT NULL,
            user_id    INTEGER   NOT NULL,
            weight     REAL      NOT NULL
        )
        """
        )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS fishing_interest(
            amount        REAL      NOT NULL,
            interest_time TIMESTAMP NOT NULL,
            jump_url      TEXT      NOT NULL,
            user_id       INTEGER   NOT NULL
        )
        """
        )

c = db.cursor()
all_fish = []
for id, entry in fish_data.items():
    print(id)
    if entry['total_caught'] == 0:
        # ignore empty entries...
        continue

    # print(entry.to_dict())
    # entry['exp'] = 5.9

    if id == 176959813509578752:  # goats
        entry['journal']['giant']['Wahoo'] += 1

    temp_exp = entry['exp']

    # remove best catch from journal
    best_catch = entry['best_catch']  # Fish object
    try:
        smell = SMELLS.index(best_catch.smell)
    except ValueError:
        # smell = int(input(f'{fish.smell} index = '))
        smell = 3

    best_catch_dict = dict(
        catch_time=fix_DT(best_catch.caught_on),
        size=best_catch.size,
        smell=smell,
        species=FISH_SPECIES[best_catch.size]['species'].index(best_catch.species),
        state=0 if best_catch in entry['inventory'] else 1,
        user_id=id,
        weight=best_catch.weight,
        )
    entry['journal'][best_catch.size][best_catch.species] -= 1
    if best_catch not in entry['inventory']:
        temp_exp -= best_catch.weight

    insert_fish(c, best_catch_dict)

    # remove fish in inventory from journal
    for fish in entry['inventory']:
        # print(fish)
        try:  # some smells are in French because I'm an idiot
            smell = SMELLS.index(fish.smell)
        except ValueError:
            # smell = int(input(f'{fish.smell} index = '))
            smell = 3

        fish_dict = dict(
            catch_time=fix_DT(fish.caught_on),
            size=fish.size,
            smell=smell,
            species=FISH_SPECIES[fish.size]['species'].index(fish.species),
            state=0,
            user_id=id,
            weight=fish.weight,
            )
        entry['journal'][fish.size][fish.species] -= 1
        insert_fish(c, fish_dict)

    for journal in entry['journal'].values():
        for species in journal:
            if journal[species] < 0:
                journal[species] -= journal[species]

    n_size = np.array([
        sum(_.values()) for _ in entry['journal'].values()
        ])

    bounds = Bounds(
        [_['weight'][0] for _ in FISH_SPECIES.values()],
        [_['weight'][1] for _ in FISH_SPECIES.values()],
        )
    # print(bounds)

    def func(weight, total_exp):
        return (total_exp - (weight * n_size).sum())**2

    while True:
        try:
            res = differential_evolution(func, bounds, args=(temp_exp,))
            if uid:
                print(entry.to_dict())
                print(n_size)
                print(res.x)

            # print(temp_exp)
            np.testing.assert_allclose((res.x * n_size).sum(), temp_exp,
                                       err_msg=f'** Fitting func = {res.fun} **')
            np.testing.assert_allclose(res.fun, 0, err_msg='** Fitting func not 0 **')

        except AssertionError:
            # print(f'{id} is bad')
            # print(entry['total_caught'])
            entry['exp'] = temp_exp = (res.x * n_size).sum()

        else:
            break

    weight = {size: res.x[i] for i, size in enumerate(FISH_SPECIES.keys())}

    for size, journal in entry['journal'].items():
        for species, amount in journal.items():
            fish_dict = dict(
                catch_time=datetime.datetime.min,
                size=size,
                smell=3,  # doesn't smell anything
                species=FISH_SPECIES[size]['species'].index(species),
                state=1,
                user_id=id,
                weight=weight[size],
                )
            for _ in range(amount):
                insert_fish(c, fish_dict)

db.commit()
c.close()
db.close()
