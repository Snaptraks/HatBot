import sqlite3
import json
import pickle


db = sqlite3.connect('HatBot.db')
db.row_factory = sqlite3.Row
