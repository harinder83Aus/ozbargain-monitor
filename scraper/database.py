"""
OzBargain Monitor - Scraper Database Module

This module imports from the shared database module to eliminate code duplication.
"""

import sys
import os

# Add the shared directory to the path
shared_path = '/app/shared'
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

# Import everything from the shared database module
exec(open('/app/shared/database.py').read())

# The exec statement above loads all the classes directly into this namespace
# We just need to create the alias for backward compatibility
DatabaseManager = ScraperDatabaseManager