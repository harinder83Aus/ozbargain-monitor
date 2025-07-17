import feedparser
import requests
import re
import logging
from datetime import datetime
from dateutil import parser as date_parser
from bs4 import BeautifulSoup
from database import DatabaseManager, Deal, SearchTerm
import time

logger = logging.getLogger(__name__)

class OzBargainScraper:
    def __init__(self, database_manager):
        self.db = database_manager
        self.user_agent = "OzBargain-Monitor/1.0"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
    def scrape_rss_feed(self, feed_url):
        """Scrape deals from OzBargain RSS feed"""
        start_time = time.time()
        deals_found = 0
        new_deals = 0
        updated_deals = 0
        error_message = None
        
        try:
            logger.info(f"Scraping RSS feed: {feed_url}")
            
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                logger.warning("No entries found in RSS feed")
                return
            
            deals_found = len(feed.entries)
            logger.info(f"Found {deals_found} deals in RSS feed")
            
            for entry in feed.entries:
                try:
                    deal_data = self._extract_deal_from_entry(entry)
                    if deal_data:
                        saved_deal, is_new = self.db.save_deal(deal_data)
                        if is_new:
                            new_deals += 1
                            self._match_deal_with_search_terms(saved_deal)
                        else:
                            updated_deals += 1
                            
                except Exception as e:
                    logger.error(f"Error processing entry: {e}")
                    continue
                    
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error scraping RSS feed: {e}")
            
        finally:
            # Log scraping activity
            scrape_duration = int(time.time() - start_time)
            log_data = {
                'scrape_type': 'rss',
                'source_url': feed_url,
                'deals_found': deals_found,
                'new_deals': new_deals,
                'updated_deals': updated_deals,
                'status': 'success' if not error_message else 'error',
                'error_message': error_message,
                'scrape_duration': scrape_duration
            }
            self.db.log_scraping_activity(log_data)
            
            logger.info(f"Scraping completed: {new_deals} new, {updated_deals} updated, {scrape_duration}s")
    
    def _extract_deal_from_entry(self, entry):
        """Extract deal information from RSS entry"""
        try:
            # Basic information
            title = entry.title
            url = entry.link
            description = entry.get('summary', '')
            
            # Parse publish date
            deal_date = None
            if hasattr(entry, 'published'):
                try:
                    deal_date = date_parser.parse(entry.published)
                except:
                    pass
            
            # Extract additional information from description HTML
            soup = BeautifulSoup(description, 'html.parser')
            
            # Try to extract price information
            price = None
            original_price = None
            discount_percentage = None
            
            # Look for price patterns in title and description
            price_match = re.search(r'\$(\d+(?:\.\d{2})?)', title)
            if price_match:
                price = float(price_match.group(1))
            
            # Look for discount percentage
            discount_match = re.search(r'(\d+)%\s*off', title, re.IGNORECASE)
            if discount_match:
                discount_percentage = int(discount_match.group(1))
            
            # Extract store name (often in title after a dash or "at")
            store = None
            store_match = re.search(r'(?:at|@)\s*([A-Za-z0-9\s]+)', title, re.IGNORECASE)
            if store_match:
                store = store_match.group(1).strip()
            
            # Extract category from RSS entry if available
            category = None
            if hasattr(entry, 'tags'):
                for tag in entry.tags:
                    if hasattr(tag, 'term'):
                        category = tag.term
                        break
            
            # Extract votes and comments from RSS extras
            votes = 0
            comments_count = 0
            
            # OzBargain RSS sometimes includes extra elements
            if hasattr(entry, 'votes'):
                try:
                    votes = int(entry.votes)
                except:
                    pass
                    
            if hasattr(entry, 'comments'):
                try:
                    comments_count = int(entry.comments)
                except:
                    pass
            
            deal_data = {
                'title': title,
                'url': url,
                'description': description,
                'price': price,
                'original_price': original_price,
                'discount_percentage': discount_percentage,
                'store': store,
                'category': category,
                'votes': votes,
                'comments_count': comments_count,
                'deal_date': deal_date,
                'is_active': True
            }
            
            return deal_data
            
        except Exception as e:
            logger.error(f"Error extracting deal from entry: {e}")
            return None
    
    def _match_deal_with_search_terms(self, deal):
        """Match a deal with active search terms"""
        try:
            search_terms = self.db.get_search_terms()
            
            for search_term in search_terms:
                match_score = self._calculate_match_score(deal, search_term)
                
                if match_score > 0.3:  # Threshold for considering a match
                    self.db.save_search_match(deal.id, search_term.id, match_score)
                    logger.info(f"Matched deal '{deal.title}' with search term '{search_term.term}' (score: {match_score})")
                    
        except Exception as e:
            logger.error(f"Error matching deal with search terms: {e}")
    
    def _calculate_match_score(self, deal, search_term):
        """Calculate match score between deal and search term"""
        try:
            term_lower = search_term.term.lower()
            title_lower = deal.title.lower()
            description_lower = (deal.description or '').lower()
            store_lower = (deal.store or '').lower()
            
            score = 0.0
            
            # Exact match in title gets highest score
            if term_lower in title_lower:
                score += 0.8
            
            # Partial word match in title
            for word in term_lower.split():
                if word in title_lower:
                    score += 0.3
            
            # Match in description
            if term_lower in description_lower:
                score += 0.4
            
            # Match in store name
            if term_lower in store_lower:
                score += 0.5
            
            # Normalize score to max 1.0
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating match score: {e}")
            return 0.0
    
    def scrape_category_feeds(self):
        """Scrape multiple category feeds"""
        categories = [
            'electrical-electronics',
            'computing',
            'gaming',
            'mobile',
            'home-garden',
            'automotive',
            'fashion-apparel',
            'books-magazines',
            'entertainment',
            'food-beverage'
        ]
        
        base_url = "https://www.ozbargain.com.au/cat"
        
        for category in categories:
            feed_url = f"{base_url}/{category}/feed"
            try:
                self.scrape_rss_feed(feed_url)
                time.sleep(2)  # Be respectful to the server
            except Exception as e:
                logger.error(f"Error scraping category {category}: {e}")
                continue