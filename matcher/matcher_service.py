import os
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from database import MatcherDatabaseManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MatcherService:
    def __init__(self, database_url):
        self.db = MatcherDatabaseManager(database_url)
        self.check_interval = 30  # Check for jobs every 30 seconds
        self.running = True
        
    def start(self):
        """Start the matcher service"""
        logger.info("Starting OzBargain Matcher Service")
        
        while self.running:
            try:
                self.process_pending_jobs()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("Shutting down matcher service")
                self.running = False
            except Exception as e:
                logger.error(f"Error in matcher service: {e}")
                time.sleep(self.check_interval)
    
    def process_pending_jobs(self):
        """Process all pending matching jobs"""
        try:
            pending_jobs = self.db.get_pending_jobs()
            
            if not pending_jobs:
                return
            
            logger.info(f"Found {len(pending_jobs)} pending matching jobs")
            
            for job in pending_jobs:
                try:
                    self.process_job(job)
                except Exception as e:
                    logger.error(f"Error processing job {job.id}: {e}")
                    self.db.mark_job_as_failed(job.id, str(e))
                    
        except Exception as e:
            logger.error(f"Error getting pending jobs: {e}")
    
    def process_job(self, job):
        """Process a single matching job"""
        logger.info(f"Processing matching job {job.id} for search term {job.search_term_id}")
        
        # Mark job as running
        self.db.mark_job_as_running(job.id)
        
        # Get search term details
        search_term = self.db.get_search_term(job.search_term_id)
        if not search_term:
            raise Exception(f"Search term {job.search_term_id} not found")
        
        if not search_term.is_active:
            logger.info(f"Search term '{search_term.term}' is not active, skipping job")
            self.db.mark_job_as_completed(job.id)
            return
        
        # Run the matching
        matches_created = self.db.run_matching_for_search_term(job.search_term_id)
        
        # Mark job as completed
        self.db.mark_job_as_completed(job.id)
        
        logger.info(f"Completed matching job {job.id}: created {matches_created} matches for search term '{search_term.term}'")
    
    def cleanup_old_jobs(self):
        """Clean up old completed/failed jobs"""
        try:
            deleted = self.db.cleanup_old_jobs(days_old=7)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old matching jobs")
        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")

def main():
    """Main function"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Wait for database to be ready
        max_retries = 30
        for attempt in range(max_retries):
            try:
                # Test database connection
                db = MatcherDatabaseManager(database_url)
                session = db.get_session()
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
                session.close()
                logger.info("Database connection established")
                break
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)
        
        # Initialize and start the matcher service
        matcher = MatcherService(database_url)
        
        # Run cleanup on startup
        matcher.cleanup_old_jobs()
        
        # Start the service
        matcher.start()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()