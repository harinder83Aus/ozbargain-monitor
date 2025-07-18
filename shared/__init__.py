"""
OzBargain Monitor - Shared Module

This module contains shared code used across all services.
"""

# Make database components available at package level
from .database import (
    # Models
    SearchTerm,
    Deal,
    SearchMatch,
    ScrapingLog,
    MatchingJob,
    Base,
    
    # Managers
    BaseDatabaseManager,
    ScraperDatabaseManager,
    MatcherDatabaseManager,
    WebDatabaseManager,
    DatabaseManager,  # Alias for backward compatibility
)

__all__ = [
    'SearchTerm',
    'Deal', 
    'SearchMatch',
    'ScrapingLog',
    'MatchingJob',
    'Base',
    'BaseDatabaseManager',
    'ScraperDatabaseManager',
    'MatcherDatabaseManager', 
    'WebDatabaseManager',
    'DatabaseManager',
]