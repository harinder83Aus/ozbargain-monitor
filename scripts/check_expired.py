#!/usr/bin/env python3
"""
Manual Expired Deal Checker Script
Allows manual triggering of expired deal checks for specific URLs or batches
"""

import os
import sys
import argparse
import logging

# Add database directory to path
sys.path.append('/app/database')
sys.path.append('../database')

try:
    from expired_checker import ExpiredDealChecker
except ImportError:
    print("Error: Could not import ExpiredDealChecker")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_specific_url(checker, url):
    """Check a specific deal URL for expiry status"""
    print(f"Checking deal: {url}")
    
    # Get deal info from database
    deals = checker.get_deals_to_check(limit=None, hours_since_check=0)
    target_deal = None
    
    for deal in deals:
        if deal['url'] == url:
            target_deal = deal
            break
    
    if not target_deal:
        print(f"Deal not found in database: {url}")
        return False
    
    # Check the deal
    is_expired = checker.check_deal_expired(url, target_deal['id'])
    
    if is_expired is None:
        print(f"❓ Inconclusive result for: {target_deal['title']}")
        return False
    elif is_expired:
        print(f"❌ EXPIRED: {target_deal['title']}")
        success = checker.update_deal_expiry_status(target_deal['id'], True)
        print(f"   Database updated: {'✅' if success else '❌'}")
    else:
        print(f"✅ ACTIVE: {target_deal['title']}")
        success = checker.update_deal_expiry_status(target_deal['id'], False)
        print(f"   Database updated: {'✅' if success else '❌'}")
    
    return True

def batch_check(checker, limit, hours_since_check):
    """Run batch expired check"""
    print(f"Running batch check (limit: {limit}, hours since check: {hours_since_check})")
    
    results = checker.run_expiry_check(limit, hours_since_check)
    
    if not results:
        print("No deals needed checking")
        return
    
    print(f"\nResults:")
    print("-" * 60)
    
    expired_count = 0
    active_count = 0
    
    for result in results:
        status = "EXPIRED" if result['is_expired'] else "ACTIVE"
        if result['is_expired']:
            expired_count += 1
        else:
            active_count += 1
            
        print(f"{status:8} | {result['title'][:45]:<45} | {result['updated']}")
    
    print("-" * 60)
    print(f"Summary: {expired_count} expired, {active_count} active deals checked")

def main():
    parser = argparse.ArgumentParser(description='Manual expired deal checker')
    parser.add_argument('--url', help='Check specific deal URL')
    parser.add_argument('--limit', type=int, default=20, help='Limit for batch check')
    parser.add_argument('--hours-since-check', type=int, default=24, help='Hours since last check for batch')
    parser.add_argument('--batch', action='store_true', help='Run batch check instead of single URL')
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL', 'postgresql://ozbargain_user:ozbargain_password@localhost:5432/ozbargain_monitor')
    
    # Initialize checker
    try:
        checker = ExpiredDealChecker(database_url)
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Run appropriate check
    try:
        if args.url:
            # Check specific URL
            success = check_specific_url(checker, args.url)
            sys.exit(0 if success else 1)
        elif args.batch:
            # Run batch check
            batch_check(checker, args.limit, args.hours_since_check)
            sys.exit(0)
        else:
            # Default: show some recently checked deals
            print("No action specified. Showing recent expired check candidates...")
            deals = checker.get_deals_to_check(limit=10, hours_since_check=24)
            
            if deals:
                print("\nDeals that could be checked:")
                print("-" * 80)
                for deal in deals:
                    last_checked = deal.get('last_checked', 'Never')
                    print(f"{deal['title'][:60]:<60} | {last_checked}")
                print("-" * 80)
                print(f"\nUse --batch to check these deals, or --url <URL> for specific check")
            else:
                print("All deals have been checked recently")
            
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"Check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()