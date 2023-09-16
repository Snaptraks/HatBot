CREATE TABLE IF NOT EXISTS giveaways_entry(
    giveaway_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (giveaway_id) REFERENCES giveaways_giveaway (giveaway_id) UNIQUE (giveaway_id, user_id)
)
