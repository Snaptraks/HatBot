SELECT EXISTS (
        SELECT 1
        FROM announcements_birthday
        WHERE user_id = :user_id
            AND guild_id = :guild_id
    )
