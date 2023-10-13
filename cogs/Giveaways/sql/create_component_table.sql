CREATE TABLE IF NOT EXISTS giveaways_component(
    component_id TEXT NOT NULL,
    name TEXT NOT NULL,
    view_id INTEGER NOT NULL,
    FOREIGN KEY (view_id) REFERENCES giveaways_view (view_id) ON DELETE CASCADE
)
