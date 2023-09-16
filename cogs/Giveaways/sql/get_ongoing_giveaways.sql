SELECT *
FROM giveaways_giveaway AS giveaway
    INNER JOIN giveaways_game AS game ON giveaway.game_id = game.game_id
WHERE is_done = 0
