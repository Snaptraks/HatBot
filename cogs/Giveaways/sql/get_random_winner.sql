SELECT *
FROM giveaways_entry
WHERE giveaway_id = :giveaway_id
ORDER BY RANDOM()
LIMIT 1
