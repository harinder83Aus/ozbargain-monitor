import os
import sys
import logging
import schedule
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify
from database import DatabaseManager
from ozbargain_scraper import OzBargainScraper

# Add database directory to Python path for expired checker
sys.path.append('/app/database')
try:
    from expired_checker import ExpiredDealChecker
except ImportError:
    logger.warning("ExpiredDealChecker not available - expired checking disabled")
    ExpiredDealChecker = None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app for health checks
app = Flask(__name__)

# Global variables
db_manager = None
scraper = None
expired_checker = None

def initialize_services():
    """Initialize database and scraper services"""
    global db_manager, scraper, expired_checker
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Initialize database
    db_manager = DatabaseManager(database_url)
    
    # Wait for database to be ready
    max_retries = 30
    for attempt in range(max_retries):
        try:
            db_manager.create_tables()
            logger.info("Database connection established and tables created")
            break
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)
    
    # Initialize scraper
    scraper = OzBargainScraper(db_manager)
    logger.info("Scraper initialized successfully")
    
    # Initialize expired deal checker if available
    if ExpiredDealChecker:
        expired_checker = ExpiredDealChecker(database_url)
        logger.info("Expired deal checker initialized successfully")
    else:
        logger.warning("Expired deal checker not available")

def run_scraping_job():
    """Run the scraping job"""
    try:
        logger.info("Starting scheduled scraping job")
        
        # Scrape main RSS feed
        main_feed_url = os.getenv('RSS_FEED_URL', 'https://www.ozbargain.com.au/deals/feed')
        scraper.scrape_rss_feed(main_feed_url)
        
        # Scrape category feeds
        scraper.scrape_category_feeds()
        
        logger.info("Scraping job completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scraping job: {e}")

def run_expired_check_job():
    """Run the expired deal checking job"""
    try:
        if not expired_checker:
            logger.debug("Expired deal checker not available, skipping")
            return
            
        logger.info("Starting expired deal check job")
        
        # Check up to 50 deals per run, focusing on deals not checked in last 24 hours
        results = expired_checker.run_expiry_check(limit=50, hours_since_check=24)
        
        if results:
            expired_count = sum(1 for r in results if r['is_expired'])
            active_count = sum(1 for r in results if not r['is_expired'])
            logger.info(f"Expired check completed: {expired_count} expired, {active_count} active deals checked")
        else:
            logger.info("No deals needed expiry checking")
        
    except Exception as e:
        logger.error(f"Error in expired deal check job: {e}")

def schedule_scraping_jobs():
    """Schedule scraping jobs"""
    scrape_interval = int(os.getenv('SCRAPE_INTERVAL', 6))
    
    # Schedule scraping every N hours
    schedule.every(scrape_interval).hours.do(run_scraping_job)
    
    # Schedule expired deal checking every 2 hours (offset from scraping)
    schedule.every(2).hours.do(run_expired_check_job)
    
    # Also run immediately on startup
    schedule.every().minute.do(run_scraping_job).tag('startup')
    
    logger.info(f"Scheduled scraping every {scrape_interval} hours and expired checking every 2 hours")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        session = db_manager.get_session()
        from sqlalchemy import text
        session.execute(text("SELECT 1"))
        session.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'database': 'healthy',
                'scraper': 'healthy'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@app.route('/status')
def status():
    """Get scraper status"""
    try:
        session = db_manager.get_session()
        
        # Get latest scraping logs
        from database import ScrapingLog
        latest_logs = session.query(ScrapingLog).order_by(ScrapingLog.created_at.desc()).limit(10).all()
        
        # Get deal count
        from database import Deal
        total_deals = session.query(Deal).count()
        active_deals = session.query(Deal).filter(Deal.is_active == True).count()
        expired_deals = session.query(Deal).filter(Deal.expiry_date.isnot(None)).count()
        
        # Get search terms count
        from database import SearchTerm
        search_terms_count = session.query(SearchTerm).filter(SearchTerm.is_active == True).count()
        
        session.close()
        
        return jsonify({
            'status': 'running',
            'timestamp': datetime.utcnow().isoformat(),
            'stats': {
                'total_deals': total_deals,
                'active_deals': active_deals,
                'expired_deals': expired_deals,
                'search_terms': search_terms_count,
                'expired_checker_enabled': expired_checker is not None
            },
            'recent_logs': [
                {
                    'scrape_type': log.scrape_type,
                    'source_url': log.source_url,
                    'deals_found': log.deals_found,
                    'new_deals': log.new_deals,
                    'status': log.status,
                    'created_at': log.created_at.isoformat()
                } for log in latest_logs
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

def run_flask_app():
    """Run Flask app in a separate thread"""
    app.run(host='0.0.0.0', port=8000, debug=False)

def main():
    """Main function"""
    try:
        logger.info("Starting OzBargain Scraper Service")
        
        # Initialize services
        initialize_services()
        
        # Start Flask app in a separate thread
        flask_thread = threading.Thread(target=run_flask_app, daemon=True)
        flask_thread.start()
        
        # Run initial scraping job
        logger.info("Running initial scraping job")
        run_scraping_job()
        
        # Clear startup job after first run
        schedule.clear('startup')
        
        # Start scheduled jobs
        logger.info("Starting scheduled scraping jobs")
        schedule_scraping_jobs()
        
    except KeyboardInterrupt:
        logger.info("Shutting down scraper service")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()