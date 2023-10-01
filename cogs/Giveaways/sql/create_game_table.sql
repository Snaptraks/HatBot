CREATE TABLE IF NOT EXISTS giveaways_game(
    game_id INTEGER NOT NULL PRIMARY KEY,
    given BOOLEAN DEFAULT 0,
    key TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    UNIQUE (key)
)
