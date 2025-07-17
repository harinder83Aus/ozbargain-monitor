#!/bin/bash

# OzBargain Monitor - Cron Job Setup Script
# Sets up automatic weekly cleanup to run every Sunday at 11 PM

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup.sh"
CRON_TIME="0 23 * * 0"  # Every Sunday at 11 PM

echo "🕐 Setting up automatic weekly cleanup for OzBargain Monitor..."

# Check if cleanup script exists
if [[ ! -f "$CLEANUP_SCRIPT" ]]; then
    echo "❌ Error: cleanup.sh not found in $SCRIPT_DIR"
    exit 1
fi

# Make sure cleanup script is executable
chmod +x "$CLEANUP_SCRIPT"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$CLEANUP_SCRIPT"; then
    echo "⚠️  Cron job already exists. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "$CLEANUP_SCRIPT" | crontab -
fi

# Add new cron job
echo "📅 Adding cron job to run every Sunday at 11 PM..."
(crontab -l 2>/dev/null; echo "$CRON_TIME $CLEANUP_SCRIPT") | crontab -

# Verify cron job was added
if crontab -l 2>/dev/null | grep -q "$CLEANUP_SCRIPT"; then
    echo "✅ Cron job successfully added:"
    echo "   Schedule: Every Sunday at 11 PM"
    echo "   Command: $CLEANUP_SCRIPT"
else
    echo "❌ Failed to add cron job"
    exit 1
fi

# Create log directory if running as root
if [[ $EUID -eq 0 ]]; then
    mkdir -p /var/log
    touch /var/log/ozbargain_cleanup.log
    chmod 644 /var/log/ozbargain_cleanup.log
    echo "📝 Log file created: /var/log/ozbargain_cleanup.log"
else
    echo "📝 Log file will be created in project directory: ./cleanup.log"
fi

# Create backup directory
if [[ $EUID -eq 0 ]]; then
    mkdir -p /var/backups/ozbargain
    chmod 755 /var/backups/ozbargain
    echo "💾 Backup directory created: /var/backups/ozbargain"
else
    mkdir -p "$SCRIPT_DIR/backups"
    echo "💾 Backup directory created: $SCRIPT_DIR/backups"
fi

echo ""
echo "🎉 Weekly cleanup setup completed!"
echo ""
echo "📋 Summary:"
echo "   • Cleanup runs every Sunday at 11 PM"
echo "   • Keeps Sunday's data, removes Monday-Saturday from previous week"
echo "   • Creates backup before cleanup"
echo "   • Logs all activities"
echo ""
echo "🔧 Management commands:"
echo "   • View cron jobs: crontab -l"
echo "   • Edit cron jobs: crontab -e"
echo "   • Remove cron job: crontab -l | grep -v '$CLEANUP_SCRIPT' | crontab -"
echo "   • Manual run: $CLEANUP_SCRIPT"
echo "   • View logs: tail -f /var/log/ozbargain_cleanup.log"
echo ""
echo "⚠️  Note: The cleanup script checks if today is Sunday before running."
echo "   Remove the day check in cleanup.sh if you want to run it manually on other days."