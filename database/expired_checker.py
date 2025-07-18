#!/usr/bin/env python3
"""
Smart Expired Deal Detection for OzBargain Monitor
Checks deal URLs to detect expired status dynamically
"""

import os
import sys
import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExpiredDealChecker:
    def __init__(self, database_url, max_workers=5, request_timeout=10):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.max_workers = max_workers
        self.request_timeout = request_timeout
        
        # Setup requests session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; OzBargainMonitor/1.0; +https://github.com/user/ozbargain-monitor)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def check_deal_expired(self, deal_url, deal_id=None):
        """Check if a single deal is expired by examining its URL content"""
        try:
            logger.debug(f"Checking deal {deal_id}: {deal_url}")
            
            # Make request with timeout
            response = self.session.get(deal_url, timeout=self.request_timeout, allow_redirects=True)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for expired indicators
            expired_indicators = [
                # Direct text indicators
                lambda s: any(text in s.get_text().lower() for text in [
                    'expired', 'this deal has expired', 'deal expired', 
                    'offer expired', 'promotion expired', 'sale ended',
                    'deal no longer available', 'offer no longer valid'
                ]),
                
                # CSS class indicators
                lambda s: any(elem.get('class', []) for elem in s.find_all() 
                           if any(cls for cls in elem.get('class', []) 
                                 if 'expired' in cls.lower() or 'ended' in cls.lower())),
                
                # Meta tag indicators
                lambda s: any(meta.get('content', '').lower() 
                             for meta in s.find_all('meta', {'name': 'description'})
                             if 'expired' in meta.get('content', '').lower()),
                
                # Specific OzBargain expired indicators
                lambda s: bool(s.find('div', class_=lambda x: x and 'expired' in x.lower())),
                lambda s: bool(s.find('span', string=lambda text: text and 'expired' in text.lower())),
                
                # Check for "Deal Expired" badges or similar
                lambda s: bool(s.find('div', string=lambda text: text and 
                                    any(phrase in text.lower() for phrase in ['deal expired', 'expired deal']))),
                
                # Check for date-based expiry (common pattern)
                lambda s: bool(s.find('time', string=lambda text: text and 
                                    datetime.now() > self._parse_deal_date(text) if self._parse_deal_date(text) else False))
            ]
            
            # Run all checks
            for check in expired_indicators:
                try:
                    if check(soup):
                        logger.info(f"Deal {deal_id} detected as expired via content check")
                        return True
                except Exception as e:
                    logger.debug(f"Expired check error for deal {deal_id}: {e}")
                    continue
            
            # Check HTTP status and redirects for additional indicators
            if response.history:
                # Deal was redirected, might indicate expiry
                final_url = response.url.lower()
                if any(term in final_url for term in ['404', 'error', 'not-found', 'expired']):
                    logger.info(f"Deal {deal_id} detected as expired via redirect")
                    return True
            
            logger.debug(f"Deal {deal_id} appears to be active")
            return False
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout checking deal {deal_id}: {deal_url}")
            return None  # Inconclusive due to timeout
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error checking deal {deal_id}: {e}")
            return None  # Inconclusive due to network error
            
        except Exception as e:
            logger.error(f"Error checking deal {deal_id}: {e}")
            return None  # Inconclusive due to error
    
    def _parse_deal_date(self, date_text):
        """Parse various date formats commonly used in deals"""
        try:
            # Common date patterns
            patterns = [
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d-%m-%Y", 
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%B %d, %Y",
                "%d %B %Y"
            ]
            
            for pattern in patterns:
                try:
                    return datetime.strptime(date_text.strip(), pattern)
                except ValueError:
                    continue
            return None
        except:
            return None
    
    def get_deals_to_check(self, limit=None, hours_since_check=24):
        """Get deals that need to be checked for expiry status"""
        session = self.SessionLocal()
        try:
            # Get deals that haven't been checked recently or are suspected expired
            cutoff_time = datetime.now() - timedelta(hours=hours_since_check)
            
            query = """
                SELECT id, url, title, created_at, expiry_date, last_checked
                FROM deals 
                WHERE (last_checked IS NULL OR last_checked < :cutoff_time)
                AND url IS NOT NULL 
                AND url != ''
                AND expiry_date IS NULL  -- Only check deals not already marked expired
                ORDER BY created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            result = session.execute(text(query), {"cutoff_time": cutoff_time})
            return [dict(row._mapping) for row in result]
            
        except Exception as e:
            logger.error(f"Error getting deals to check: {e}")
            return []
        finally:
            session.close()
    
    def update_deal_expiry_status(self, deal_id, is_expired, checked_at=None):
        """Update deal expiry status in database"""
        session = self.SessionLocal()
        try:
            if checked_at is None:
                checked_at = datetime.now()
            
            if is_expired:
                # Mark deal as expired
                session.execute(text("""
                    UPDATE deals 
                    SET expiry_date = :checked_at, last_checked = :checked_at
                    WHERE id = :deal_id
                """), {
                    "deal_id": deal_id,
                    "checked_at": checked_at
                })
                logger.info(f"Marked deal {deal_id} as expired")
            else:
                # Update last checked timestamp
                session.execute(text("""
                    UPDATE deals 
                    SET last_checked = :checked_at
                    WHERE id = :deal_id
                """), {
                    "deal_id": deal_id,
                    "checked_at": checked_at
                })
                logger.debug(f"Updated last_checked for deal {deal_id}")
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating deal {deal_id} expiry status: {e}")
            return False
        finally:
            session.close()
    
    def check_deals_batch(self, deals):
        """Check multiple deals in parallel"""
        results = []
        checked_at = datetime.now()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_deal = {
                executor.submit(self.check_deal_expired, deal['url'], deal['id']): deal 
                for deal in deals
            }
            
            # Process results as they complete
            for future in as_completed(future_to_deal):
                deal = future_to_deal[future]
                try:
                    is_expired = future.result()
                    
                    if is_expired is not None:  # Only update if we got a conclusive result
                        success = self.update_deal_expiry_status(deal['id'], is_expired, checked_at)
                        results.append({
                            'deal_id': deal['id'],
                            'url': deal['url'],
                            'title': deal['title'],
                            'is_expired': is_expired,
                            'updated': success
                        })
                    else:
                        logger.warning(f"Inconclusive result for deal {deal['id']}, skipping update")
                        
                except Exception as e:
                    logger.error(f"Error processing deal {deal['id']}: {e}")
                
                # Rate limiting - small delay between requests
                time.sleep(0.5)
        
        return results
    
    def run_expiry_check(self, limit=None, hours_since_check=24):
        """Run expired deal detection on batch of deals"""
        logger.info("Starting expired deal detection")
        
        # Get deals to check
        deals = self.get_deals_to_check(limit, hours_since_check)
        
        if not deals:
            logger.info("No deals need to be checked")
            return []
        
        logger.info(f"Checking {len(deals)} deals for expiry status")
        
        # Check deals in batches
        results = self.check_deals_batch(deals)
        
        # Summary
        expired_count = sum(1 for r in results if r['is_expired'])
        active_count = sum(1 for r in results if not r['is_expired'])
        
        logger.info(f"Expiry check completed: {expired_count} expired, {active_count} active deals")
        
        return results

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart expired deal detection')
    parser.add_argument('--limit', type=int, help='Limit number of deals to check')
    parser.add_argument('--hours-since-check', type=int, default=24, help='Hours since last check')
    parser.add_argument('--max-workers', type=int, default=5, help='Maximum concurrent workers')
    
    args = parser.parse_args()
    
    database_url = os.getenv('DATABASE_URL', 'postgresql://ozbargain_user:ozbargain_password@postgres:5432/ozbargain_monitor')
    
    checker = ExpiredDealChecker(database_url, max_workers=args.max_workers)
    
    try:
        results = checker.run_expiry_check(args.limit, args.hours_since_check)
        
        if results:
            print("\nExpiry Check Results:")
            print("-" * 50)
            for result in results:
                status = "EXPIRED" if result['is_expired'] else "ACTIVE"
                print(f"Deal {result['deal_id']}: {status}")
                print(f"  Title: {result['title'][:60]}...")
                print(f"  URL: {result['url']}")
                print()
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Expired deal check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()