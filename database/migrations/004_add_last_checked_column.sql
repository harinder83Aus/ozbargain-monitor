-- Migration: Add last_checked column to deals table for smart expiry detection
-- Date: 2025-07-18
-- Description: Adds last_checked timestamp to track when deals were last verified for expiry status

BEGIN;

-- Add last_checked column to deals table
ALTER TABLE deals ADD COLUMN IF NOT EXISTS last_checked TIMESTAMP;

-- Add index for efficient querying of deals that need checking
CREATE INDEX IF NOT EXISTS idx_deals_last_checked ON deals(last_checked) WHERE last_checked IS NOT NULL;

-- Create index for expired deals query optimization
CREATE INDEX IF NOT EXISTS idx_deals_expiry_status ON deals(expiry_date, last_checked) WHERE expiry_date IS NULL;

-- Add comment to document the column purpose
COMMENT ON COLUMN deals.last_checked IS 'Timestamp when deal was last checked for expiry status via URL content verification';

-- Update the trigger function to use the new column
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

-- Record migration
INSERT INTO schema_migrations (migration_name, checksum) 
VALUES ('004_add_last_checked_column', '004_last_checked_v1') 
ON CONFLICT (migration_name) DO NOTHING;

COMMIT;