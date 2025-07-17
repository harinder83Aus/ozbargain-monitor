#!/usr/bin/env python3
"""
OzBargain Monitor - Match Existing Deals Script

This script matches existing deals with search terms that were added after the deals were scraped.
Useful when you add new search terms and want to find matches in historical data.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add the scraper directory to the path
sys.path.append('/home/harry/ozbargain-monitor/scraper')

from database import DatabaseManager, Deal, SearchTerm
from ozbargain_scraper import OzBargainScraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to match existing deals with search terms"""
    
    print("🔍 OzBargain Monitor - Match Existing Deals")
    print("=" * 50)
    
    try:
        # Get database URL
        database_url = os.getenv('DATABASE_URL', 'postgresql://ozbargain_user:ozbargain_password@localhost:5432/ozbargain_monitor')
        
        # Initialize database manager
        db_manager = DatabaseManager(database_url)
        
        # Get statistics before matching
        session = db_manager.get_session()
        total_deals = session.query(Deal).count()
        total_search_terms = session.query(SearchTerm).filter(SearchTerm.is_active == True).count()
        existing_matches = session.execute("SELECT COUNT(*) FROM search_matches").scalar()
        session.close()
        
        print(f"📊 Current Statistics:")
        print(f"   • Total deals: {total_deals}")
        print(f"   • Active search terms: {total_search_terms}")
        print(f"   • Existing matches: {existing_matches}")
        print()
        
        if total_search_terms == 0:
            print("⚠️  No active search terms found. Please add search terms first.")
            return
        
        if total_deals == 0:
            print("⚠️  No deals found in database. Please run the scraper first.")
            return
        
        # Ask for confirmation
        response = input("Do you want to match existing deals with your search terms? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled.")
            return
        
        print("🚀 Starting matching process...")
        
        # Initialize scraper for matching logic
        scraper = OzBargainScraper(db_manager)
        
        # Get all deals and search terms
        session = db_manager.get_session()
        deals = session.query(Deal).filter(Deal.is_active == True).all()
        search_terms = session.query(SearchTerm).filter(SearchTerm.is_active == True).all()
        session.close()
        
        print(f"🎯 Processing {len(deals)} deals against {len(search_terms)} search terms...")
        
        matches_found = 0
        
        # Match each deal with search terms
        for i, deal in enumerate(deals, 1):
            if i % 50 == 0:
                print(f"   Processed {i}/{len(deals)} deals...")
            
            # Use the scraper's matching logic
            try:
                for search_term in search_terms:
                    match_score = scraper._calculate_match_score(deal, search_term)
                    
                    if match_score > 0.3:  # Same threshold as in scraper
                        # Check if match already exists
                        session = db_manager.get_session()
                        existing_match = session.query(db_manager.SessionLocal().execute(
                            "SELECT 1 FROM search_matches WHERE deal_id = :deal_id AND search_term_id = :search_term_id",
                            {'deal_id': deal.id, 'search_term_id': search_term.id}
                        ).fetchone())
                        session.close()
                        
                        if not existing_match:
                            db_manager.save_search_match(deal.id, search_term.id, match_score)
                            matches_found += 1
                            logger.info(f"Matched deal '{deal.title}' with search term '{search_term.term}' (score: {match_score:.2f})")
                            
            except Exception as e:
                logger.error(f"Error matching deal {deal.id}: {e}")
                continue
        
        print(f"✅ Matching completed!")
        print(f"   • New matches found: {matches_found}")
        
        # Get final statistics
        session = db_manager.get_session()
        final_matches = session.execute("SELECT COUNT(*) FROM search_matches").scalar()
        session.close()
        
        print(f"   • Total matches now: {final_matches}")
        print()
        print("🎉 You can now view your matched deals in the web interface!")
        print("   Visit: http://localhost:5000/matched-deals")
        
    except Exception as e:
        logger.error(f"Error during matching process: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()