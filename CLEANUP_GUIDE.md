# OzBargain Monitor - Data Cleanup Guide

## Overview

The OzBargain Monitor includes an automated cleanup system that maintains optimal database performance by removing old data while preserving important records. The system is designed to keep Sunday's data as reference points while cleaning up the previous week's daily data.

## Cleanup Strategy

### What Gets Cleaned
- **Deals**: Monday-Saturday data from the previous week
- **Search Matches**: Matching records for the cleaned deals
- **Scraping Logs**: Logs from the cleaned period

### What Gets Preserved
- **Sunday Data**: Always preserved as weekly reference points
- **Search Terms**: Never deleted (user-configured data)
- **Recent Data**: Last 7 days are always kept

### Cleanup Schedule
- **Frequency**: Weekly (every Sunday at 11 PM)
- **Data Retention**: Keeps Sunday data indefinitely, removes Monday-Saturday after 1 week
- **Backup**: Creates compressed backup before each cleanup

## Files

### 1. cleanup.sh
Main cleanup script that performs the weekly data maintenance.

**Features:**
- Calculates date ranges automatically
- Creates backup before cleanup
- Preserves Sunday data
- Removes Monday-Saturday from previous week
- Logs all activities
- Vacuum database after cleanup
- Error handling and notifications

### 2. setup_cron.sh
Sets up automated weekly cleanup using cron.

**Usage:**
```bash
# Install automatic cleanup
./setup_cron.sh

# This will:
# - Add cron job for Sunday 11 PM
# - Create log directories
# - Create backup directories
# - Set proper permissions
```

### 3. manual_cleanup.sh
For testing and immediate cleanup without waiting for Sunday.

**Usage:**
```bash
# Run cleanup manually (any day)
./manual_cleanup.sh

# Shows before/after statistics
# Asks for confirmation
# Bypasses Sunday-only restriction
```

## Installation

### 1. Set Up Automatic Cleanup
```bash
# Navigate to project directory
cd ozbargain-monitor

# Install automated cleanup
./setup_cron.sh
```

### 2. Verify Installation
```bash
# Check cron job was added
crontab -l

# Should show:
# 0 23 * * 0 /path/to/ozbargain-monitor/cleanup.sh
```

## Usage

### Automatic Operation
Once installed, the cleanup runs automatically every Sunday at 11 PM. No manual intervention required.

### Manual Operation
```bash
# Test cleanup (any day)
./manual_cleanup.sh

# View cleanup logs
tail -f /var/log/ozbargain_cleanup.log
# or (if not root)
tail -f ./cleanup.log
```

### Monitoring
```bash
# View recent cleanup activity
tail -20 /var/log/ozbargain_cleanup.log

# Check cron job status
systemctl status cron

# View cron logs
grep ozbargain /var/log/syslog
```

## Configuration

### Customize Cleanup Time
Edit the cron job to change when cleanup runs:
```bash
crontab -e

# Change from Sunday 11 PM to Friday 2 AM:
# 0 2 * * 5 /path/to/cleanup.sh
```

### Customize Retention Policy
Edit `cleanup.sh` to change what gets preserved:

```bash
# To preserve more days, modify the date calculations:
# Currently: Keeps Sunday, removes Mon-Sat
# To keep Fri-Sun: Modify CLEANUP_START and CLEANUP_END calculations
```

### Notification Settings
Edit the `send_notification()` function in `cleanup.sh` to add email/Slack notifications:

```bash
# Example email notification:
send_notification() {
    local status=$1
    local message=$2
    echo "$message" | mail -s "OzBargain Cleanup $status" admin@example.com
}
```

## Backup Management

### Backup Location
- **Root user**: `/var/backups/ozbargain/`
- **Regular user**: `./backups/`

### Backup Retention
- Automatic cleanup keeps last 4 backups (28 days)
- Backups are compressed with gzip
- Backup filename format: `ozbargain_backup_YYYYMMDD_HHMMSS.sql.gz`

### Manual Backup
```bash
# Create manual backup
docker compose exec postgres pg_dump -U ozbargain_user ozbargain_monitor > backup.sql

# Restore from backup
docker compose exec -T postgres psql -U ozbargain_user -d ozbargain_monitor < backup.sql
```

## Troubleshooting

### Common Issues

#### 1. Cleanup Not Running
```bash
# Check if cron service is running
systemctl status cron

# Check cron job exists
crontab -l

# Check logs for errors
grep ozbargain /var/log/syslog
```

#### 2. Database Connection Failed
```bash
# Check if containers are running
docker compose ps

# Check database health
docker compose exec postgres pg_isready -U ozbargain_user -d ozbargain_monitor

# Restart containers if needed
docker compose restart
```

#### 3. Permission Issues
```bash
# Check script permissions
ls -la cleanup.sh

# Make executable if needed
chmod +x cleanup.sh

# Check log file permissions
ls -la /var/log/ozbargain_cleanup.log
```

#### 4. Backup Creation Failed
```bash
# Check backup directory permissions
ls -la /var/backups/ozbargain/

# Check disk space
df -h

# Test manual backup
docker compose exec postgres pg_dump -U ozbargain_user ozbargain_monitor > test_backup.sql
```

### Error Messages

#### "Database container not running"
- **Cause**: Docker containers are stopped
- **Solution**: Start containers with `docker compose up -d`

#### "Failed to create backup"
- **Cause**: Disk space or permission issues
- **Solution**: Check disk space (`df -h`) and permissions

#### "No records to clean up"
- **Cause**: No data in the cleanup date range
- **Solution**: Normal operation, no action needed

## Monitoring & Maintenance

### Weekly Checks
```bash
# Check cleanup logs
tail -50 /var/log/ozbargain_cleanup.log

# Check database size
docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -c "
    SELECT pg_size_pretty(pg_total_relation_size('deals')) as deals_size,
           pg_size_pretty(pg_total_relation_size('search_matches')) as matches_size,
           pg_size_pretty(pg_total_relation_size('scraping_logs')) as logs_size;
"

# Check record counts
docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -c "
    SELECT 'deals' as table_name, COUNT(*) as records FROM deals
    UNION ALL
    SELECT 'search_matches', COUNT(*) FROM search_matches
    UNION ALL
    SELECT 'scraping_logs', COUNT(*) FROM scraping_logs;
"
```

### Monthly Maintenance
```bash
# Clean old backups manually
find /var/backups/ozbargain/ -name "*.sql.gz" -type f -mtime +60 -delete

# Check disk usage trends
df -h /var/backups/ozbargain/

# Vacuum database manually if needed
docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -c "VACUUM ANALYZE;"
```

## Security Considerations

### File Permissions
- Scripts should be executable only by intended users
- Log files should be readable by administrators only
- Backup files contain sensitive data and should be secured

### Database Security
- Cleanup script uses existing database credentials
- No additional permissions required
- Backups contain full database content

### Cron Security
- Cron jobs run with user privileges
- Use absolute paths in cron jobs
- Ensure script directory is secure

## Performance Impact

### During Cleanup
- Database operations may be slower during cleanup
- Backup creation requires additional disk I/O
- Vacuum operation at end may take several minutes

### After Cleanup
- Improved query performance due to smaller tables
- Reduced disk usage
- Better backup/restore times

## Recovery Procedures

### Restore from Backup
```bash
# Stop application
docker compose down

# Start only database
docker compose up -d postgres

# Wait for database to be ready
docker compose exec postgres pg_isready -U ozbargain_user -d ozbargain_monitor

# Restore from backup
gunzip -c /var/backups/ozbargain/backup_file.sql.gz | docker compose exec -T postgres psql -U ozbargain_user -d ozbargain_monitor

# Restart all services
docker compose up -d
```

### Emergency Stop
```bash
# Stop cleanup if running
pkill -f cleanup.sh

# Check for running processes
ps aux | grep cleanup

# Remove cron job if needed
crontab -l | grep -v cleanup.sh | crontab -
```

This cleanup system ensures your OzBargain Monitor maintains optimal performance while preserving important data according to your specified retention policy.