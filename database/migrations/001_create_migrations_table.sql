-- Migration 001: Create migrations tracking table
-- This table tracks which migrations have been applied
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT NOW(),
    checksum VARCHAR(64) NOT NULL
);

-- Insert this migration as applied
INSERT INTO schema_migrations (migration_name, checksum) 
VALUES ('001_create_migrations_table', 'baseline') 
ON CONFLICT (migration_name) DO NOTHING;