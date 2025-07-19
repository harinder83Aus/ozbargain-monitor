"""
OzBargain Monitor - Shared Database Module

This module consolidates all database models and managers from the scraper, matcher, and web services.
All services should import from this shared module to eliminate code duplication.
"""

import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, DECIMAL, ForeignKey, desc, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

Base = declarative_base()

# Database Models
class SearchTerm(Base):
    __tablename__ = 'search_terms'
    
    id = Column(Integer, primary_key=True)
    term = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    matches = relationship("SearchMatch", back_populates="search_term")

class Deal(Base):
    __tablename__ = 'deals'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    price = Column(DECIMAL(10, 2))
    original_price = Column(DECIMAL(10, 2))
    discount_percentage = Column(Integer)
    store = Column(String(255))
    category = Column(String(100))
    votes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    deal_date = Column(DateTime)
    expiry_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    matches = relationship("SearchMatch", back_populates="deal")

class SearchMatch(Base):
    __tablename__ = 'search_matches'
    
    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey('deals.id', ondelete='CASCADE'), nullable=False)
    search_term_id = Column(Integer, ForeignKey('search_terms.id', ondelete='CASCADE'), nullable=False)
    match_score = Column(DECIMAL(3, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    deal = relationship("Deal", back_populates="matches")
    search_term = relationship("SearchTerm", back_populates="matches")

class ScrapingLog(Base):
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True)
    scrape_type = Column(String(50), nullable=False)
    source_url = Column(Text, nullable=False)
    deals_found = Column(Integer, default=0)
    new_deals = Column(Integer, default=0)
    updated_deals = Column(Integer, default=0)
    status = Column(String(20), default='success')
    error_message = Column(Text)
    scrape_duration = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class MatchingJob(Base):
    __tablename__ = 'matching_jobs'
    
    id = Column(Integer, primary_key=True)
    search_term_id = Column(Integer, ForeignKey('search_terms.id', ondelete='CASCADE'), nullable=False)
    job_type = Column(String(50), nullable=False, default='new_search_term')
    status = Column(String(20), nullable=False, default='pending')
    scheduled_at = Column(DateTime, nullable=False)
    executed_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Base Database Manager
class BaseDatabaseManager:
    """Base database manager with common functionality"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_session(self):
        return self.SessionLocal()
    
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
    
    def get_search_terms(self, include_inactive=False):
        session = self.get_session()
        try:
            if include_inactive:
                return session.query(SearchTerm).order_by(SearchTerm.is_active.desc(), SearchTerm.created_at.desc()).all()
            else:
                return session.query(SearchTerm).filter(SearchTerm.is_active == True).order_by(SearchTerm.created_at.desc()).all()
        finally:
            session.close()

# Scraper Database Manager
class ScraperDatabaseManager(BaseDatabaseManager):
    """Database manager for scraper service"""
    
    def save_deal(self, deal_data):
        session = self.get_session()
        try:
            # Check if deal already exists
            existing_deal = session.query(Deal).filter(Deal.url == deal_data['url']).first()
            
            if existing_deal:
                # Update existing deal
                for key, value in deal_data.items():
                    setattr(existing_deal, key, value)
                existing_deal.updated_at = datetime.utcnow()
                session.commit()
                return existing_deal, False
            else:
                # Create new deal
                new_deal = Deal(**deal_data)
                session.add(new_deal)
                session.commit()
                return new_deal, True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving deal: {e}")
            raise
        finally:
            session.close()
    
    def save_search_match(self, deal_id, search_term_id, match_score):
        session = self.get_session()
        try:
            # Check if match already exists
            existing_match = session.query(SearchMatch).filter(
                SearchMatch.deal_id == deal_id,
                SearchMatch.search_term_id == search_term_id
            ).first()
            
            if not existing_match:
                new_match = SearchMatch(
                    deal_id=deal_id,
                    search_term_id=search_term_id,
                    match_score=match_score
                )
                session.add(new_match)
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving search match: {e}")
            raise
        finally:
            session.close()
    
    def log_scraping_activity(self, log_data):
        session = self.get_session()
        try:
            log_entry = ScrapingLog(**log_data)
            session.add(log_entry)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging scraping activity: {e}")
            raise
        finally:
            session.close()

# Matcher Database Manager
class MatcherDatabaseManager(BaseDatabaseManager):
    """Database manager for matcher service"""
    
    def get_pending_jobs(self):
        """Get matching jobs that are ready to be executed"""
        session = self.get_session()
        try:
            return session.query(MatchingJob).filter(
                MatchingJob.status == 'pending',
                MatchingJob.scheduled_at <= datetime.utcnow()
            ).all()
        finally:
            session.close()
    
    def mark_job_as_running(self, job_id):
        """Mark a job as currently running"""
        session = self.get_session()
        try:
            job = session.query(MatchingJob).filter(MatchingJob.id == job_id).first()
            if job:
                job.status = 'running'
                job.executed_at = datetime.utcnow()
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking job as running: {e}")
            raise
        finally:
            session.close()
    
    def mark_job_as_completed(self, job_id):
        """Mark a job as completed"""
        session = self.get_session()
        try:
            job = session.query(MatchingJob).filter(MatchingJob.id == job_id).first()
            if job:
                job.status = 'completed'
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking job as completed: {e}")
            raise
        finally:
            session.close()
    
    def mark_job_as_failed(self, job_id, error_message):
        """Mark a job as failed with error message"""
        session = self.get_session()
        try:
            job = session.query(MatchingJob).filter(MatchingJob.id == job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = error_message
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking job as failed: {e}")
            raise
        finally:
            session.close()
    
    def get_search_term(self, search_term_id):
        """Get a specific search term"""
        session = self.get_session()
        try:
            return session.query(SearchTerm).filter(SearchTerm.id == search_term_id).first()
        finally:
            session.close()
    
    def run_matching_for_search_term(self, search_term_id):
        """Run matching for a specific search term using SQL"""
        session = self.get_session()
        try:
            # Use raw SQL for better performance
            sql = text("""
                WITH deal_matches AS (
                    SELECT 
                        d.id as deal_id,
                        :search_term_id as search_term_id,
                        CASE 
                            WHEN LOWER(d.title) LIKE '%' || LOWER(st.term) || '%' THEN 0.8
                            WHEN LOWER(d.store) LIKE '%' || LOWER(st.term) || '%' THEN 0.5
                            WHEN LOWER(d.description) LIKE '%' || LOWER(st.term) || '%' THEN 0.4
                            ELSE 0.0
                        END as match_score
                    FROM deals d
                    CROSS JOIN search_terms st
                    WHERE d.is_active = true 
                    AND st.is_active = true
                    AND st.id = :search_term_id
                    AND LOWER(d.title) NOT LIKE '%expired%'
                    AND LOWER(d.title) NOT LIKE '%(expired)%'
                    AND (d.expiry_date IS NULL OR d.expiry_date > NOW())
                    AND (
                        LOWER(d.title) LIKE '%' || LOWER(st.term) || '%' OR
                        LOWER(d.store) LIKE '%' || LOWER(st.term) || '%' OR
                        LOWER(d.description) LIKE '%' || LOWER(st.term) || '%'
                    )
                )
                INSERT INTO search_matches (deal_id, search_term_id, match_score, created_at)
                SELECT deal_id, search_term_id, match_score, NOW()
                FROM deal_matches
                WHERE match_score > 0.3
                AND NOT EXISTS (
                    SELECT 1 FROM search_matches sm 
                    WHERE sm.deal_id = deal_matches.deal_id 
                    AND sm.search_term_id = deal_matches.search_term_id
                )
            """)
            
            result = session.execute(sql, {'search_term_id': search_term_id})
            session.commit()
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error running matching for search term {search_term_id}: {e}")
            raise
        finally:
            session.close()
    
    def cleanup_old_jobs(self, days_old=7):
        """Clean up old completed/failed jobs"""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            deleted = session.query(MatchingJob).filter(
                MatchingJob.status.in_(['completed', 'failed']),
                MatchingJob.created_at < cutoff_date
            ).delete()
            session.commit()
            return deleted
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up old jobs: {e}")
            raise
        finally:
            session.close()

# Web Database Manager
class WebDatabaseManager(BaseDatabaseManager):
    """Database manager for web service"""
    
    def get_recent_deals(self, limit=50, store_filter=None):
        session = self.get_session()
        try:
            query = session.query(Deal).filter(
                Deal.is_active == True,
                ~Deal.title.ilike('%expired%'),  # Exclude deals marked as expired
                ~Deal.title.ilike('%(expired)%'),  # Also exclude deals with (expired) pattern
                (Deal.expiry_date.is_(None)) | (Deal.expiry_date > datetime.utcnow())  # Exclude past expiry dates
            )
            
            # Add store filter if provided
            if store_filter:
                query = query.filter(Deal.store.ilike(f'%{store_filter}%'))
            
            return query.order_by(desc(Deal.created_at)).limit(limit).all()
        finally:
            session.close()
    
    def get_available_stores(self, min_deals=2):
        """Get list of stores with at least min_deals active deals"""
        session = self.get_session()
        try:
            return session.query(Deal.store, func.count(Deal.id).label('deal_count')).filter(
                Deal.is_active == True,
                Deal.store.isnot(None),
                ~Deal.title.ilike('%expired%'),
                ~Deal.title.ilike('%(expired)%'),
                (Deal.expiry_date.is_(None)) | (Deal.expiry_date > datetime.utcnow()),
                func.length(Deal.store) > 3  # Filter out truncated store names
            ).group_by(Deal.store).having(func.count(Deal.id) >= min_deals).order_by(desc(func.count(Deal.id))).all()
        finally:
            session.close()
    
    def get_matched_deals(self, search_term_id=None, limit=50):
        session = self.get_session()
        try:
            query = session.query(Deal).join(SearchMatch).join(SearchTerm).filter(
                Deal.is_active == True,
                SearchTerm.is_active == True,  # Only show matches for active search terms
                ~Deal.title.ilike('%expired%'),  # Exclude deals marked as expired
                ~Deal.title.ilike('%(expired)%')  # Also exclude deals with (expired) pattern
            )
            
            # Also exclude deals with expiry_date in the past
            query = query.filter(
                (Deal.expiry_date.is_(None)) | (Deal.expiry_date > datetime.utcnow())
            )
            
            if search_term_id:
                query = query.filter(SearchMatch.search_term_id == search_term_id)
            
            return query.order_by(desc(Deal.created_at)).limit(limit).all()
        finally:
            session.close()
    
    def add_search_term(self, term, description=None, immediate_search=False):
        session = self.get_session()
        try:
            search_term = SearchTerm(term=term, description=description)
            session.add(search_term)
            session.commit()
            
            # Get the ID and create a detached object to return
            term_id = search_term.id
            term_data = {
                'id': search_term.id,
                'term': search_term.term,
                'description': search_term.description,
                'is_active': search_term.is_active
            }
            
            # If immediate search is requested, update the matching job to run now
            if immediate_search:
                # The trigger already created a job scheduled for 5 minutes from now
                # Let's update it to run immediately
                session.execute(
                    text("UPDATE matching_jobs SET scheduled_at = NOW() WHERE search_term_id = :term_id AND status = 'pending'"),
                    {'term_id': term_id}
                )
                session.commit()
            
            # Create a new detached object with the data
            result_term = SearchTerm()
            for key, value in term_data.items():
                setattr(result_term, key, value)
            
            return result_term
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_search_term(self, term_id, term=None, description=None, is_active=None):
        session = self.get_session()
        try:
            search_term = session.query(SearchTerm).filter(SearchTerm.id == term_id).first()
            if search_term:
                if term is not None:
                    search_term.term = term
                if description is not None:
                    search_term.description = description
                if is_active is not None:
                    search_term.is_active = is_active
                search_term.updated_at = datetime.utcnow()
                session.commit()
                return search_term
            return None
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_search_term(self, term_id):
        session = self.get_session()
        try:
            search_term = session.query(SearchTerm).filter(SearchTerm.id == term_id).first()
            if search_term:
                search_term.is_active = False
                search_term.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_scraping_logs(self, limit=20):
        session = self.get_session()
        try:
            return session.query(ScrapingLog).order_by(desc(ScrapingLog.created_at)).limit(limit).all()
        finally:
            session.close()
    
    def get_statistics(self):
        session = self.get_session()
        try:
            stats = {}
            stats['total_deals'] = session.query(Deal).count()
            
            # Active deals (excluding expired ones)
            stats['active_deals'] = session.query(Deal).filter(
                Deal.is_active == True,
                ~Deal.title.ilike('%expired%'),
                ~Deal.title.ilike('%(expired)%'),
                (Deal.expiry_date.is_(None)) | (Deal.expiry_date > datetime.utcnow())
            ).count()
            
            stats['search_terms'] = session.query(SearchTerm).filter(SearchTerm.is_active == True).count()
            
            # Matched deals (excluding expired ones)
            stats['matched_deals'] = session.query(SearchMatch).join(Deal).filter(
                Deal.is_active == True,
                ~Deal.title.ilike('%expired%'),
                ~Deal.title.ilike('%(expired)%'),
                (Deal.expiry_date.is_(None)) | (Deal.expiry_date > datetime.utcnow())
            ).count()
            
            return stats
        finally:
            session.close()
    
    def mark_deal_as_expired(self, deal_id):
        """Mark a deal as expired by setting expiry_date to past"""
        session = self.get_session()
        try:
            deal = session.query(Deal).filter(Deal.id == deal_id).first()
            if deal:
                deal.expiry_date = datetime.utcnow() - timedelta(days=1)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking deal as expired: {e}")
            raise
        finally:
            session.close()
    
    def get_expired_deals_count(self):
        """Get count of expired deals"""
        session = self.get_session()
        try:
            return session.query(Deal).filter(
                Deal.is_active == True,
                ((Deal.title.ilike('%expired%')) | 
                 (Deal.title.ilike('%(expired)%')) |
                 ((Deal.expiry_date.isnot(None)) & (Deal.expiry_date <= datetime.utcnow())))
            ).count()
        finally:
            session.close()
    
    def purge_search_matches(self, search_term_id):
        """Purge all search matches for a specific search term"""
        session = self.get_session()
        try:
            deleted_count = session.query(SearchMatch).filter(SearchMatch.search_term_id == search_term_id).count()
            session.query(SearchMatch).filter(SearchMatch.search_term_id == search_term_id).delete()
            session.commit()
            return deleted_count
        except Exception as e:
            session.rollback()
            logger.error(f"Error purging search matches for term {search_term_id}: {e}")
            raise
        finally:
            session.close()
    
    def run_immediate_matching(self, search_term_id):
        """Run immediate matching for a search term using the same logic as matcher service"""
        session = self.get_session()
        try:
            # Use the same SQL logic as the matcher service
            sql = text("""
                WITH deal_matches AS (
                    SELECT 
                        d.id as deal_id,
                        :search_term_id as search_term_id,
                        CASE 
                            WHEN LOWER(d.title) LIKE '%' || LOWER(st.term) || '%' THEN 0.8
                            WHEN LOWER(d.store) LIKE '%' || LOWER(st.term) || '%' THEN 0.5
                            WHEN LOWER(d.description) LIKE '%' || LOWER(st.term) || '%' THEN 0.4
                            ELSE 0.0
                        END as match_score
                    FROM deals d
                    CROSS JOIN search_terms st
                    WHERE d.is_active = true 
                    AND st.is_active = true
                    AND st.id = :search_term_id
                    AND LOWER(d.title) NOT LIKE '%expired%'
                    AND LOWER(d.title) NOT LIKE '%(expired)%'
                    AND (d.expiry_date IS NULL OR d.expiry_date > NOW())
                    AND (
                        LOWER(d.title) LIKE '%' || LOWER(st.term) || '%' OR
                        LOWER(d.store) LIKE '%' || LOWER(st.term) || '%' OR
                        LOWER(d.description) LIKE '%' || LOWER(st.term) || '%'
                    )
                )
                INSERT INTO search_matches (deal_id, search_term_id, match_score, created_at)
                SELECT deal_id, search_term_id, match_score, NOW()
                FROM deal_matches
                WHERE match_score > 0.3
                AND NOT EXISTS (
                    SELECT 1 FROM search_matches sm 
                    WHERE sm.deal_id = deal_matches.deal_id 
                    AND sm.search_term_id = deal_matches.search_term_id
                )
            """)
            
            result = session.execute(sql, {'search_term_id': search_term_id})
            session.commit()
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error running immediate matching for search term {search_term_id}: {e}")
            raise
        finally:
            session.close()

# Compatibility aliases for backward compatibility
DatabaseManager = WebDatabaseManager  # Default to web manager for backward compatibility