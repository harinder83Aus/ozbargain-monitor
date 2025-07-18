-- Migration: Smart Expired Deal Detection
-- Date: 2025-07-18
-- Description: Replaces hardcoded expired deal marking with smart URL-based detection

BEGIN;

-- Remove any hardcoded expired deals from the old system
-- We'll let the smart checker handle these dynamically
UPDATE deals 
SET expiry_date = NULL, last_checked = NULL
WHERE url = 'https://www.ozbargain.com.au/node/912724'
  AND expiry_date = '2025-01-17'::timestamp;

-- Create a procedure to trigger smart expired checking on specific deals
CREATE OR REPLACE FUNCTION trigger_expired_check_for_deal(deal_url TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    deal_count INTEGER;
BEGIN
    -- Check if deal exists
    SELECT COUNT(*) INTO deal_count 
    FROM deals 
    WHERE url = deal_url;
    
    IF deal_count > 0 THEN
        -- Reset last_checked to force re-checking
        UPDATE deals 
        SET last_checked = NULL 
        WHERE url = deal_url;
        
        RETURN TRUE;
    ELSE
        RETURN FALSE;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Add comment explaining the smart detection approach
COMMENT ON FUNCTION trigger_expired_check_for_deal(TEXT) IS 'Triggers smart expired checking for a specific deal URL by resetting its last_checked timestamp';

-- Schedule the previously hardcoded deal for smart checking
SELECT trigger_expired_check_for_deal('https://www.ozbargain.com.au/node/912724');

-- Record migration
INSERT INTO schema_migrations (migration_name, checksum) 
VALUES ('003_smart_expired_detection', '003_smart_detection_v1') 
ON CONFLICT (migration_name) DO NOTHING;

COMMIT;