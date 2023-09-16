SELECT *
FROM giveaways_game
WHERE given = 0
ORDER BY RANDOM()
LIMIT 1
