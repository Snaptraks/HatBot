import sqlite3
import json
import pickle


db = sqlite3.connect('HatBot.db')
db.row_factory = sqlite3.Row


with db:
    c = db.execute('SELECT * FROM fishing_fish')
    print(f'{len(c.fetchall())} total fish in DB')

    c = db.execute('SELECT * FROM fishing_fish GROUP BY user_id')
    print(f'{len(c.fetchall())} total users in DB')

    for size in FISH_SPECIES.keys():
        c = db.execute('SELECT * FROM fishing_fish WHERE size = ?', (size,))
        print(f'{len(c.fetchall())} {size} fish')

    c = db.execute('SELECT * FROM fishing_fish WHERE user_id = 337266376941240320')
    print(len(c.fetchall()))
    print(fish_data[337266376941240320]['total_caught'])
