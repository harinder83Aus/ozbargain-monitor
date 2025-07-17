#!/bin/bash

# OzBargain Monitor - Manual Cleanup Script
# For testing and immediate cleanup without waiting for Sunday

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup.sh"

echo "🧹 Manual OzBargain Monitor Cleanup"
echo "=================================="

# Check if cleanup script exists
if [[ ! -f "$CLEANUP_SCRIPT" ]]; then
    echo "❌ Error: cleanup.sh not found in $SCRIPT_DIR"
    exit 1
fi

# Show current data before cleanup
echo "📊 Current database statistics:"
docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -c "
    SELECT 
        'deals' as table_name, 
        COUNT(*) as total_records,
        MIN(created_at) as oldest_record,
        MAX(created_at) as newest_record
    FROM deals
    WHERE created_at IS NOT NULL
    UNION ALL
    SELECT 
        'search_matches' as table_name,
        COUNT(*) as total_records,
        MIN(created_at) as oldest_record,
        MAX(created_at) as newest_record
    FROM search_matches
    WHERE created_at IS NOT NULL
    UNION ALL
    SELECT 
        'scraping_logs' as table_name,
        COUNT(*) as total_records,
        MIN(created_at) as oldest_record,
        MAX(created_at) as newest_record
    FROM scraping_logs
    WHERE created_at IS NOT NULL;
"

echo ""
echo "⚠️  This will run the cleanup script regardless of the day."
echo "   The script will preserve Sunday's data and remove Monday-Saturday from the previous week."
echo ""

# Ask for confirmation
read -p "Do you want to proceed with the cleanup? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

echo "🚀 Starting manual cleanup..."

# Create a temporary version of the cleanup script without the Sunday check
TEMP_CLEANUP="/tmp/ozbargain_manual_cleanup.sh"
sed 's/if \[\[ $(date +%w) -ne 0 \]\]; then/if false; then/' "$CLEANUP_SCRIPT" > "$TEMP_CLEANUP"
chmod +x "$TEMP_CLEANUP"

# Run the cleanup
if "$TEMP_CLEANUP"; then
    echo "✅ Manual cleanup completed successfully!"
    
    # Show statistics after cleanup
    echo ""
    echo "📊 Database statistics after cleanup:"
    docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -c "
        SELECT 
            'deals' as table_name, 
            COUNT(*) as total_records,
            MIN(created_at) as oldest_record,
            MAX(created_at) as newest_record
        FROM deals
        WHERE created_at IS NOT NULL
        UNION ALL
        SELECT 
            'search_matches' as table_name,
            COUNT(*) as total_records,
            MIN(created_at) as oldest_record,
            MAX(created_at) as newest_record
        FROM search_matches
        WHERE created_at IS NOT NULL
        UNION ALL
        SELECT 
            'scraping_logs' as table_name,
            COUNT(*) as total_records,
            MIN(created_at) as oldest_record,
            MAX(created_at) as newest_record
        FROM scraping_logs
        WHERE created_at IS NOT NULL;
    "
else
    echo "❌ Manual cleanup failed!"
    exit 1
fi

# Clean up temporary file
rm -f "$TEMP_CLEANUP"

echo ""
echo "🎉 Manual cleanup process completed!"
echo "📝 Check the log file for detailed information."