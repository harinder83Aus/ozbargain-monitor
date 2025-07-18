-- Migration 002: Mark manually identified expired deals
-- This migration marks deals that are expired on OzBargain but not automatically detected

-- Mark the Kayo Sports deal as expired (manually verified on OzBargain website)
UPDATE deals 
SET expiry_date = '2025-01-17'::timestamp 
WHERE url = 'https://www.ozbargain.com.au/node/912724'
  AND expiry_date IS NULL;

-- Record this migration as applied
INSERT INTO schema_migrations (migration_name, checksum) 
VALUES ('002_mark_expired_deals', 'kayo_expired_fix') 
ON CONFLICT (migration_name) DO NOTHING;