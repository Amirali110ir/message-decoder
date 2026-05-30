ALTER TABLE users ADD COLUMN referral_code TEXT;
ALTER TABLE users ADD COLUMN referred_by_user_id TEXT;
ALTER TABLE users ADD COLUMN referral_awarded_at TEXT;
ALTER TABLE telegram_sessions ADD COLUMN pending_referral_code TEXT;

CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);
