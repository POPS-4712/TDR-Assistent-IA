CREATE TABLE IF NOT EXISTS assistant_processed_items (
  item_key TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  title TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assistant_processed_source_at
  ON assistant_processed_items (source, processed_at DESC);
