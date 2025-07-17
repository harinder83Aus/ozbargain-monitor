#!/bin/bash

# OzBargain Monitor - Weekly Data Cleanup Script
# Runs every Sunday night to clean up the previous week's data
# Keeps Sunday's data and purges Monday-Saturday from the previous week

set -e

# Configuration
DB_CONTAINER="ozbargain_db"
DB_NAME="ozbargain_monitor"
DB_USER="ozbargain_user"
LOG_FILE="/var/log/ozbargain_cleanup.log"
BACKUP_DIR="/var/backups/ozbargain"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if script is running as root (for logging)
check_permissions() {
    if [[ $EUID -ne 0 ]]; then
        log_message "WARNING: Running as non-root user. Log file may not be accessible."
        LOG_FILE="./cleanup.log"
    fi
}

# Function to create backup directory
create_backup_dir() {
    if [[ $EUID -eq 0 ]]; then
        mkdir -p "$BACKUP_DIR"
    else
        BACKUP_DIR="./backups"
        mkdir -p "$BACKUP_DIR"
    fi
}

# Function to check if Docker container is running
check_docker_container() {
    if ! docker compose ps | grep -q "$DB_CONTAINER.*Up"; then
        log_message "ERROR: Database container '$DB_CONTAINER' is not running"
        exit 1
    fi
    log_message "INFO: Database container is running"
}

# Function to create backup before cleanup
create_backup() {
    local backup_file="$BACKUP_DIR/ozbargain_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    log_message "INFO: Creating backup before cleanup..."
    
    if docker compose exec postgres pg_dump -U "$DB_USER" "$DB_NAME" > "$backup_file"; then
        log_message "INFO: Backup created successfully: $backup_file"
        
        # Compress the backup
        gzip "$backup_file"
        log_message "INFO: Backup compressed: ${backup_file}.gz"
        
        # Keep only last 4 backups (1 month)
        find "$BACKUP_DIR" -name "ozbargain_backup_*.sql.gz" -type f -mtime +28 -delete 2>/dev/null || true
        log_message "INFO: Old backups cleaned up"
    else
        log_message "ERROR: Failed to create backup"
        exit 1
    fi
}

# Function to calculate date ranges
calculate_dates() {
    # Get last Sunday (if today is Sunday, get last Sunday, not today)
    local days_since_sunday=$(date +%w)
    if [[ $days_since_sunday -eq 0 ]]; then
        # Today is Sunday, get last Sunday
        LAST_SUNDAY=$(date -d "7 days ago" +%Y-%m-%d)
    else
        # Get the most recent Sunday
        LAST_SUNDAY=$(date -d "$days_since_sunday days ago" +%Y-%m-%d)
    fi
    
    # Calculate the Monday of the week before last Sunday
    CLEANUP_START=$(date -d "$LAST_SUNDAY - 6 days" +%Y-%m-%d)
    
    # Calculate the Saturday of the week before last Sunday  
    CLEANUP_END=$(date -d "$LAST_SUNDAY - 1 day" +%Y-%m-%d)
    
    log_message "INFO: Cleanup date range: $CLEANUP_START to $CLEANUP_END (Monday to Saturday)"
    log_message "INFO: Preserving Sunday data: $LAST_SUNDAY"
}

# Function to get record counts before cleanup
get_record_counts_before() {
    DEALS_BEFORE=$(docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM deals WHERE created_at >= '$CLEANUP_START 00:00:00' AND created_at <= '$CLEANUP_END 23:59:59';" | xargs)
    MATCHES_BEFORE=$(docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM search_matches WHERE created_at >= '$CLEANUP_START 00:00:00' AND created_at <= '$CLEANUP_END 23:59:59';" | xargs)
    LOGS_BEFORE=$(docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM scraping_logs WHERE created_at >= '$CLEANUP_START 00:00:00' AND created_at <= '$CLEANUP_END 23:59:59';" | xargs)
    
    log_message "INFO: Records to be cleaned - Deals: $DEALS_BEFORE, Matches: $MATCHES_BEFORE, Logs: $LOGS_BEFORE"
}

# Function to perform cleanup
perform_cleanup() {
    log_message "INFO: Starting cleanup process..."
    
    # Clean up search_matches first (due to foreign key constraints)
    log_message "INFO: Cleaning up search matches..."
    docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
        DELETE FROM search_matches 
        WHERE created_at >= '$CLEANUP_START 00:00:00' 
        AND created_at <= '$CLEANUP_END 23:59:59';
    "
    
    # Clean up deals
    log_message "INFO: Cleaning up deals..."
    docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
        DELETE FROM deals 
        WHERE created_at >= '$CLEANUP_START 00:00:00' 
        AND created_at <= '$CLEANUP_END 23:59:59';
    "
    
    # Clean up scraping logs
    log_message "INFO: Cleaning up scraping logs..."
    docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
        DELETE FROM scraping_logs 
        WHERE created_at >= '$CLEANUP_START 00:00:00' 
        AND created_at <= '$CLEANUP_END 23:59:59';
    "
    
    log_message "INFO: Cleanup completed successfully"
}

# Function to get record counts after cleanup
get_record_counts_after() {
    DEALS_AFTER=$(docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM deals;" | xargs)
    MATCHES_AFTER=$(docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM search_matches;" | xargs)
    LOGS_AFTER=$(docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM scraping_logs;" | xargs)
    
    log_message "INFO: Records after cleanup - Deals: $DEALS_AFTER, Matches: $MATCHES_AFTER, Logs: $LOGS_AFTER"
}

# Function to vacuum database
vacuum_database() {
    log_message "INFO: Running database vacuum to reclaim space..."
    docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -c "VACUUM ANALYZE;"
    log_message "INFO: Database vacuum completed"
}

# Function to check disk space
check_disk_space() {
    local disk_usage=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
    log_message "INFO: Current disk usage: ${disk_usage}%"
    
    if [[ $disk_usage -gt 90 ]]; then
        log_message "WARNING: Disk usage is high (${disk_usage}%)"
    fi
}

# Function to send notification (optional)
send_notification() {
    local status=$1
    local message=$2
    
    # You can customize this to send notifications via email, Slack, etc.
    # For now, just log the notification
    log_message "NOTIFICATION: $status - $message"
    
    # Example: Send email notification (uncomment and configure if needed)
    # echo "$message" | mail -s "OzBargain Monitor Cleanup $status" admin@example.com
}

# Main execution
main() {
    log_message "INFO: Starting OzBargain Monitor weekly cleanup"
    
    # Check if it's Sunday (optional - remove this check if you want to run manually)
    if [[ $(date +%w) -ne 0 ]]; then
        log_message "INFO: Not Sunday, exiting (remove this check for manual runs)"
        exit 0
    fi
    
    # Initialize
    check_permissions
    create_backup_dir
    
    # Navigate to project directory
    cd "$(dirname "$0")"
    
    # Check prerequisites
    check_docker_container
    
    # Calculate date ranges
    calculate_dates
    
    # Get initial counts
    get_record_counts_before
    
    # Skip cleanup if no records to clean
    if [[ $DEALS_BEFORE -eq 0 && $MATCHES_BEFORE -eq 0 && $LOGS_BEFORE -eq 0 ]]; then
        log_message "INFO: No records to clean up, exiting"
        exit 0
    fi
    
    # Create backup
    create_backup
    
    # Perform cleanup
    perform_cleanup
    
    # Get final counts
    get_record_counts_after
    
    # Vacuum database
    vacuum_database
    
    # Check disk space
    check_disk_space
    
    # Calculate cleaned records
    local deals_cleaned=$((DEALS_BEFORE))
    local matches_cleaned=$((MATCHES_BEFORE))
    local logs_cleaned=$((LOGS_BEFORE))
    
    local summary="Cleanup completed successfully. Cleaned: $deals_cleaned deals, $matches_cleaned matches, $logs_cleaned logs. Date range: $CLEANUP_START to $CLEANUP_END"
    
    log_message "INFO: $summary"
    send_notification "SUCCESS" "$summary"
    
    log_message "INFO: Weekly cleanup completed successfully"
}

# Error handling
trap 'log_message "ERROR: Script failed at line $LINENO"; send_notification "FAILED" "Cleanup script failed at line $LINENO"; exit 1' ERR

# Run main function
main "$@"