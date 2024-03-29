CREATE TABLE IF NOT EXISTS giveaways_giveaway(
    giveaway_id INTEGER NOT NULL PRIMARY KEY,
    channel_id INTEGER,
    created_at TIMESTAMP,
    game_id INTEGER NOT NULL,
    is_done BOOLEAN DEFAULT 0,
    message_id INTEGER,
    trigger_at TIMESTAMP NOT NULL,
    FOREIGN KEY (game_id) REFERENCES giveaways_game (game_id)
)
