import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, DECIMAL, ForeignKey, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class SearchTerm(Base):
    __tablename__ = 'search_terms'
    
    id = Column(Integer, primary_key=True)
    term = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
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
    
    matches = relationship("SearchMatch", back_populates="deal")

class SearchMatch(Base):
    __tablename__ = 'search_matches'
    
    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey('deals.id', ondelete='CASCADE'), nullable=False)
    search_term_id = Column(Integer, ForeignKey('search_terms.id', ondelete='CASCADE'), nullable=False)
    match_score = Column(DECIMAL(3, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    
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

class DatabaseManager:
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_session(self):
        return self.SessionLocal()
    
    def get_recent_deals(self, limit=50):
        session = self.get_session()
        try:
            from datetime import datetime
            return session.query(Deal).filter(
                Deal.is_active == True,
                ~Deal.title.ilike('%expired%'),  # Exclude deals marked as expired
                ~Deal.title.ilike('%(expired)%'),  # Also exclude deals with (expired) pattern
                (Deal.expiry_date.is_(None)) | (Deal.expiry_date > datetime.utcnow())  # Exclude past expiry dates
            ).order_by(desc(Deal.created_at)).limit(limit).all()
        finally:
            session.close()
    
    def get_matched_deals(self, search_term_id=None, limit=50):
        session = self.get_session()
        try:
            query = session.query(Deal).join(SearchMatch).filter(
                Deal.is_active == True,
                ~Deal.title.ilike('%expired%'),  # Exclude deals marked as expired
                ~Deal.title.ilike('%(expired)%')  # Also exclude deals with (expired) pattern
            )
            
            # Also exclude deals with expiry_date in the past
            from datetime import datetime
            query = query.filter(
                (Deal.expiry_date.is_(None)) | (Deal.expiry_date > datetime.utcnow())
            )
            
            if search_term_id:
                query = query.filter(SearchMatch.search_term_id == search_term_id)
            
            return query.order_by(desc(Deal.created_at)).limit(limit).all()
        finally:
            session.close()
    
    def get_search_terms(self):
        session = self.get_session()
        try:
            return session.query(SearchTerm).filter(SearchTerm.is_active == True).all()
        finally:
            session.close()
    
    def add_search_term(self, term, description=None):
        session = self.get_session()
        try:
            search_term = SearchTerm(term=term, description=description)
            session.add(search_term)
            session.commit()
            return search_term
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
            from datetime import datetime
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
            from datetime import datetime, timedelta
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
            from datetime import datetime
            return session.query(Deal).filter(
                Deal.is_active == True,
                ((Deal.title.ilike('%expired%')) | 
                 (Deal.title.ilike('%(expired)%')) |
                 ((Deal.expiry_date.isnot(None)) & (Deal.expiry_date <= datetime.utcnow())))
            ).count()
        finally:
            session.close()