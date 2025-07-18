# Database Tools

This directory contains database management tools for the OzBargain Monitor system.

## Components

### Migration System (`migrate.py`)
- Automatically applies SQL migrations in order
- Tracks applied migrations to prevent duplicates
- Validates migration checksums for integrity

### Backup System (`backup.py`)
- Creates timestamped database backups
- Verifies backup integrity
- Supports different backup types (manual, pre-deployment, post-deployment)
- Automatic cleanup of old backups

### Smart Expired Deal Detection (`expired_checker.py`)
- Checks deal URLs for expired status by analyzing content
- Replaces hardcoded expired deal marking
- Runs in parallel with configurable concurrency
- Updates database with expiry status and last-checked timestamps

## Usage

### Running Migrations
```bash
# In Docker container
python /app/migrate.py

# Or via Docker Compose
docker compose exec web python /app/migrate.py
```

### Creating Backups
```bash
# Manual backup
python /app/database/backup.py backup --type manual

# Verify data integrity
python /app/database/backup.py verify

# Cleanup old backups
python /app/database/backup.py cleanup
```

### Checking Expired Deals
```bash
# Batch check (up to 50 deals)
python /app/database/expired_checker.py --limit 50

# Check specific URL
python /app/scripts/check_expired.py --url "https://www.ozbargain.com.au/node/12345"

# Batch check via script
python /app/scripts/check_expired.py --batch --limit 20
```

## Jenkins Integration

The Jenkins pipeline automatically:
1. Creates pre-deployment backups
2. Runs migrations
3. Verifies data integrity post-migration
4. Creates post-deployment backups
5. Cleans up old backup files

## Database Schema

### New Columns
- `deals.last_checked` - Timestamp when deal was last verified for expiry
- Enhanced indexing for efficient expired deal queries

### Migration Files
- `001_create_migrations_table.sql` - Initial migration tracking
- `002_mark_expired_deals.sql` - Legacy hardcoded expiry (deprecated)
- `003_smart_expired_detection.sql` - Smart detection migration
- `004_add_last_checked_column.sql` - Last checked column addition

## Smart Expired Detection

The system now intelligently detects expired deals by:

1. **Content Analysis**: Parsing deal pages for expired indicators
2. **Pattern Matching**: Detecting common expiry markers and text
3. **Redirect Detection**: Identifying deals redirected to error pages
4. **Rate Limiting**: Respectful scraping with delays between requests
5. **Parallel Processing**: Checking multiple deals concurrently

### Detection Patterns
- Text indicators: "expired", "deal expired", "offer ended"
- CSS classes: elements with "expired" or "ended" classes
- Meta descriptions: expired status in page metadata
- Redirects: URLs redirecting to 404 or error pages

### Automation
- Runs every 2 hours via scraper service
- Checks deals not verified in last 24 hours
- Automatically updates database with expiry status
- Logs all checking activity for monitoring