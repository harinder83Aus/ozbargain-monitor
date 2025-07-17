import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, DECIMAL, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

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

class DatabaseManager:
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_session(self):
        return self.SessionLocal()
    
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
    
    def get_search_terms(self):
        session = self.get_session()
        try:
            return session.query(SearchTerm).filter(SearchTerm.is_active == True).all()
        finally:
            session.close()
    
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