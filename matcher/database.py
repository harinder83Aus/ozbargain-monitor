import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, DECIMAL, ForeignKey, desc, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class SearchTerm(Base):
    __tablename__ = 'search_terms'
    
    id = Column(Integer, primary_key=True)
    term = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

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

class SearchMatch(Base):
    __tablename__ = 'search_matches'
    
    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey('deals.id', ondelete='CASCADE'), nullable=False)
    search_term_id = Column(Integer, ForeignKey('search_terms.id', ondelete='CASCADE'), nullable=False)
    match_score = Column(DECIMAL(3, 2))
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

class MatcherDatabaseManager:
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_session(self):
        return self.SessionLocal()
    
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