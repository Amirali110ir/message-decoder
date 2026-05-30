CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  phone TEXT UNIQUE,
  telegram_id TEXT UNIQUE NOT NULL,
  credit_balance INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS telegram_sessions (
  telegram_id TEXT PRIMARY KEY,
  chat_id TEXT NOT NULL,
  user_id TEXT,
  state TEXT NOT NULL DEFAULT 'awaiting_contact',
  message_text TEXT,
  relationship_type TEXT,
  user_goal TEXT,
  last_free_json TEXT,
  ghost_mode INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decodes (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  message_text TEXT,
  relationship_type TEXT NOT NULL,
  user_goal TEXT NOT NULL,
  free_json TEXT NOT NULL,
  paid_json TEXT,
  created_at TEXT NOT NULL,
  paid_at TEXT
);
