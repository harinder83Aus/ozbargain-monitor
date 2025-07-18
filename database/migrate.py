#!/usr/bin/env python3
"""
Database Migration Runner for OzBargain Monitor
Automatically applies pending migrations in order
"""

import os
import sys
import hashlib
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self, database_url, migrations_dir):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.migrations_dir = Path(migrations_dir)
        
    def get_migration_checksum(self, migration_content):
        """Generate checksum for migration content"""
        return hashlib.sha256(migration_content.encode()).hexdigest()[:16]
    
    def get_applied_migrations(self):
        """Get list of already applied migrations"""
        session = self.SessionLocal()
        try:
            # Create migrations table if it doesn't exist
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT NOW(),
                    checksum VARCHAR(64) NOT NULL
                );
            """))
            session.commit()
            
            result = session.execute(text("SELECT migration_name FROM schema_migrations ORDER BY migration_name"))
            return {row[0] for row in result}
        except Exception as e:
            session.rollback()
            logger.error(f"Error getting applied migrations: {e}")
            return set()
        finally:
            session.close()
    
    def apply_migration(self, migration_file):
        """Apply a single migration file"""
        session = self.SessionLocal()
        try:
            logger.info(f"Applying migration: {migration_file.name}")
            
            # Read migration content
            with open(migration_file, 'r') as f:
                migration_content = f.read()
            
            # Generate checksum
            checksum = self.get_migration_checksum(migration_content)
            
            # Execute migration
            session.execute(text(migration_content))
            
            # Record migration as applied (if not already recorded by the migration itself)
            session.execute(text("""
                INSERT INTO schema_migrations (migration_name, checksum) 
                VALUES (:name, :checksum) 
                ON CONFLICT (migration_name) DO NOTHING
            """), {"name": migration_file.stem, "checksum": checksum})
            
            session.commit()
            logger.info(f"Successfully applied migration: {migration_file.name}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error applying migration {migration_file.name}: {e}")
            return False
        finally:
            session.close()
    
    def run_migrations(self):
        """Run all pending migrations"""
        logger.info("Starting database migrations...")
        
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return False
        
        # Get applied migrations
        applied_migrations = self.get_applied_migrations()
        logger.info(f"Already applied migrations: {applied_migrations}")
        
        # Get all migration files
        migration_files = sorted([
            f for f in self.migrations_dir.glob("*.sql") 
            if f.is_file()
        ])
        
        if not migration_files:
            logger.info("No migration files found")
            return True
        
        # Apply pending migrations
        applied_count = 0
        for migration_file in migration_files:
            migration_name = migration_file.stem
            
            if migration_name not in applied_migrations:
                if self.apply_migration(migration_file):
                    applied_count += 1
                else:
                    logger.error(f"Failed to apply migration: {migration_name}")
                    return False
            else:
                logger.info(f"Skipping already applied migration: {migration_name}")
        
        if applied_count > 0:
            logger.info(f"Successfully applied {applied_count} new migrations")
        else:
            logger.info("No new migrations to apply")
        
        return True

def main():
    """Main entry point"""
    database_url = os.getenv('DATABASE_URL', 'postgresql://ozbargain_user:ozbargain_password@localhost:5432/ozbargain_monitor')
    migrations_dir = os.getenv('MIGRATIONS_DIR', '/app/migrations')
    
    logger.info(f"Database URL: {database_url}")
    logger.info(f"Migrations directory: {migrations_dir}")
    
    runner = MigrationRunner(database_url, migrations_dir)
    
    if runner.run_migrations():
        logger.info("All migrations completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)

if __name__ == "__main__":
    main()