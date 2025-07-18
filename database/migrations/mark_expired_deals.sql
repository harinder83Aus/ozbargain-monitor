-- Migration: Mark manually identified expired deals
-- Date: 2025-01-18
-- Purpose: Mark deals that are expired on OzBargain but not automatically detected

-- Mark the Kayo Sports deal as expired (manually verified on OzBargain website)
UPDATE deals 
SET expiry_date = '2025-01-17'::timestamp 
WHERE url = 'https://www.ozbargain.com.au/node/912724'
  AND expiry_date IS NULL;

-- Future: Add more expired deals here as they are identified
-- Example:
-- UPDATE deals SET expiry_date = 'YYYY-MM-DD'::timestamp WHERE url = 'https://www.ozbargain.com.au/node/XXXXXX';