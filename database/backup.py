#!/usr/bin/env python3
"""
Database Backup and Restoration for OzBargain Monitor
Creates timestamped backups and validates data integrity
"""

import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseBackup:
    def __init__(self, database_url, backup_dir):
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse database URL for pg_dump
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Extract connection details
        url_parts = database_url.split('://')[-1]  # Remove postgresql://
        user_host = url_parts.split('@')
        if len(user_host) == 2:
            user_pass = user_host[0].split(':')
            self.db_user = user_pass[0]
            self.db_password = user_pass[1] if len(user_pass) > 1 else ""
            host_db = user_host[1].split('/')
            self.db_host = host_db[0].split(':')[0]
            self.db_port = host_db[0].split(':')[1] if ':' in host_db[0] else "5432"
            self.db_name = host_db[1]
        else:
            logger.error("Invalid database URL format")
            raise ValueError("Invalid database URL format")
    
    def create_backup(self, backup_type="scheduled"):
        """Create a database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"ozbargain_backup_{backup_type}_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename
        
        try:
            logger.info(f"Creating {backup_type} backup: {backup_filename}")
            
            # Set environment variables for pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password
            
            # Create backup using pg_dump
            cmd = [
                'pg_dump',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', self.db_name,
                '--verbose',
                '--clean',
                '--if-exists',
                '--no-owner',
                '--no-privileges'
            ]
            
            with open(backup_path, 'w') as backup_file:
                result = subprocess.run(
                    cmd,
                    stdout=backup_file,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )
            
            if result.returncode == 0:
                # Get backup file size
                backup_size = backup_path.stat().st_size
                logger.info(f"Backup completed successfully: {backup_filename} ({backup_size:,} bytes)")
                
                # Verify backup integrity
                if self.verify_backup_integrity(backup_path):
                    logger.info("Backup integrity verified")
                    return backup_path
                else:
                    logger.error("Backup integrity check failed")
                    backup_path.unlink()  # Delete invalid backup
                    return None
            else:
                logger.error(f"Backup failed: {result.stderr}")
                if backup_path.exists():
                    backup_path.unlink()
                return None
                
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            if backup_path.exists():
                backup_path.unlink()
            return None
    
    def verify_backup_integrity(self, backup_path):
        """Verify backup file contains expected content"""
        try:
            with open(backup_path, 'r') as f:
                content = f.read()
            
            # Check for essential elements
            required_elements = [
                'CREATE TABLE deals',
                'CREATE TABLE search_terms', 
                'CREATE TABLE search_matches',
                'CREATE TABLE schema_migrations'
            ]
            
            for element in required_elements:
                if element not in content:
                    logger.error(f"Backup missing required element: {element}")
                    return False
            
            # Check backup is not empty
            if len(content) < 1000:  # Minimum expected size
                logger.error("Backup file too small, likely incomplete")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error verifying backup integrity: {e}")
            return False
    
    def verify_data_integrity(self):
        """Verify current database data integrity"""
        session = self.SessionLocal()
        try:
            # Check core tables exist and have data
            checks = [
                ("deals", "SELECT COUNT(*) FROM deals"),
                ("search_terms", "SELECT COUNT(*) FROM search_terms"),
                ("search_matches", "SELECT COUNT(*) FROM search_matches"),
                ("schema_migrations", "SELECT COUNT(*) FROM schema_migrations")
            ]
            
            results = {}
            for table_name, query in checks:
                try:
                    result = session.execute(text(query)).scalar()
                    results[table_name] = result
                    logger.info(f"{table_name}: {result} records")
                except Exception as e:
                    logger.error(f"Error checking {table_name}: {e}")
                    return False, {}
            
            # Verify referential integrity
            integrity_checks = [
                "SELECT COUNT(*) FROM search_matches sm LEFT JOIN deals d ON sm.deal_id = d.id WHERE d.id IS NULL",
                "SELECT COUNT(*) FROM search_matches sm LEFT JOIN search_terms st ON sm.search_term_id = st.id WHERE st.id IS NULL"
            ]
            
            for check in integrity_checks:
                orphaned = session.execute(text(check)).scalar()
                if orphaned > 0:
                    logger.warning(f"Found {orphaned} orphaned records")
            
            return True, results
            
        except Exception as e:
            logger.error(f"Error checking data integrity: {e}")
            return False, {}
        finally:
            session.close()
    
    def cleanup_old_backups(self, keep_count=10):
        """Remove old backup files, keeping only the most recent ones"""
        try:
            backup_files = sorted(
                self.backup_dir.glob("ozbargain_backup_*.sql"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if len(backup_files) > keep_count:
                files_to_remove = backup_files[keep_count:]
                for backup_file in files_to_remove:
                    logger.info(f"Removing old backup: {backup_file.name}")
                    backup_file.unlink()
                    
                logger.info(f"Cleaned up {len(files_to_remove)} old backup files")
            else:
                logger.info(f"No cleanup needed ({len(backup_files)} backups, keeping {keep_count})")
                
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database backup and verification tool')
    parser.add_argument('action', choices=['backup', 'verify', 'cleanup'], help='Action to perform')
    parser.add_argument('--type', default='manual', help='Backup type (manual, pre-deployment, post-deployment)')
    parser.add_argument('--backup-dir', default='/app/backups', help='Backup directory')
    
    args = parser.parse_args()
    
    database_url = os.getenv('DATABASE_URL', 'postgresql://ozbargain_user:ozbargain_password@postgres:5432/ozbargain_monitor')
    
    backup_tool = DatabaseBackup(database_url, args.backup_dir)
    
    if args.action == 'backup':
        backup_path = backup_tool.create_backup(args.type)
        if backup_path:
            logger.info(f"Backup created successfully: {backup_path}")
            sys.exit(0)
        else:
            logger.error("Backup failed")
            sys.exit(1)
            
    elif args.action == 'verify':
        success, results = backup_tool.verify_data_integrity()
        if success:
            logger.info("Data integrity verification passed")
            for table, count in results.items():
                print(f"{table}: {count} records")
            sys.exit(0)
        else:
            logger.error("Data integrity verification failed")
            sys.exit(1)
            
    elif args.action == 'cleanup':
        backup_tool.cleanup_old_backups()
        logger.info("Backup cleanup completed")
        sys.exit(0)

if __name__ == "__main__":
    main()