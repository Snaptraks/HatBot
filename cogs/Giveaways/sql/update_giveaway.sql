UPDATE giveaways_giveaway
SET channel_id = :channel_id,
    created_at = :created_at,
    message_id = :message_id
WHERE giveaway_id = :giveaway_id
