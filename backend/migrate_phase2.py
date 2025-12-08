"""
Database migration script for Phase 2: Semantic Chunking

This script adds the chunk_hashes table for deduplication tracking.

Run this script once to update your database schema.
"""

import logging
from sqlalchemy import text
from app.infrastructure.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_phase2_migrations():
    """Run Phase 2 migrations for semantic chunking features."""
    db = SessionLocal()
    
    try:
        logger.info("Starting Phase 2 migrations...")
        
        # Create chunk_hashes table
        logger.info("Creating chunk_hashes table...")
        
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS chunk_hashes (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                document_id INTEGER NOT NULL REFERENCES documents(id),
                content_hash VARCHAR(64) NOT NULL UNIQUE,
                chunk_index INTEGER NOT NULL,
                char_count INTEGER,
                word_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Create indexes
        logger.info("Creating indexes...")
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_chunk_hashes_tenant_id
            ON chunk_hashes(tenant_id);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_chunk_hashes_document_id
            ON chunk_hashes(document_id);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_chunk_hashes_content_hash
            ON chunk_hashes(content_hash);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_chunk_hash_tenant_doc
            ON chunk_hashes(tenant_id, document_id);
        """))
        
        db.commit()
        logger.info("✅ Phase 2 migrations completed successfully!")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info("✅ Created chunk_hashes table for deduplication")
        logger.info("✅ Created indexes for efficient hash lookups")
        logger.info("\n📋 Next steps:")
        logger.info("1. Re-upload documents to use semantic chunking")
        logger.info("2. Old chunks (naive) will remain in Qdrant")
        logger.info("3. New chunks will have better structure and overlap")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_phase2_migrations()
