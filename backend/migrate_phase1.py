"""
Database migration script for Phase 1: Observability Foundation

This script adds the necessary tables and columns for:
- Feedback tracking (feedbacks table)
- Query logging (query_logs table)
- Document metadata (category, language, content_hash, version columns)

Run this script once to update your database schema.
"""

import logging
from sqlalchemy import text
from app.infrastructure.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_phase1_migrations():
    """Run Phase 1 migrations for observability features."""
    db = SessionLocal()
    
    try:
        logger.info("Starting Phase 1 migrations...")
        
        # 1. Add metadata columns to documents table
        logger.info("Adding metadata columns to documents table...")
        
        db.execute(text("""
            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS category VARCHAR(100);
        """))
        
        db.execute(text("""
            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'pt-BR';
        """))
        
        db.execute(text("""
            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS page_count INTEGER;
        """))
        
        db.execute(text("""
            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_documents_content_hash
            ON documents(content_hash);
        """))
        
        db.execute(text("""
            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
        """))
        
        # 2. Create feedbacks table
        logger.info("Creating feedbacks table...")
        
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating IN (1, 5)),
                comment TEXT,
                chunks_used JSONB,
                avg_score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_feedbacks_tenant_id
            ON feedbacks(tenant_id);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_feedbacks_created_at
            ON feedbacks(created_at);
        """))
        
        # 3. Create query_logs table
        logger.info("Creating query_logs table...")
        
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                question TEXT NOT NULL,
                chunks_retrieved INTEGER DEFAULT 0,
                chunks_used JSONB,
                avg_score FLOAT,
                min_score FLOAT,
                max_score FLOAT,
                response_time_ms INTEGER,
                embedding_time_ms INTEGER,
                retrieval_time_ms INTEGER,
                llm_time_ms INTEGER,
                tokens_used INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_query_logs_tenant_id
            ON query_logs(tenant_id);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_query_logs_created_at
            ON query_logs(created_at);
        """))
        
        db.commit()
        logger.info("✅ Phase 1 migrations completed successfully!")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info("✅ Added metadata columns to documents table:")
        logger.info("   - category, language, page_count, content_hash, version")
        logger.info("✅ Created feedbacks table for user satisfaction tracking")
        logger.info("✅ Created query_logs table for performance monitoring")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_phase1_migrations()
