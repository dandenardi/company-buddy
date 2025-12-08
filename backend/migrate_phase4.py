"""
Database migration script for Phase 4: Conversational Context

This script adds the conversations and messages tables for session tracking.

Run this script once to update your database schema.
"""

import logging
from sqlalchemy import text
from app.infrastructure.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_phase4_migrations():
    """Run Phase 4 migrations for conversational context features."""
    db = SessionLocal()
    
    try:
        logger.info("Starting Phase 4 migrations...")
        
        # 1. Create conversations table
        logger.info("Creating conversations table...")
        
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                title VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id
            ON conversations(tenant_id);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id
            ON conversations(user_id);
        """))
        
        # 2. Create messages table
        logger.info("Creating messages table...")
        
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                chunks_used JSONB,
                rewritten_query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
            ON messages(conversation_id);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_messages_created_at
            ON messages(created_at);
        """))
        
        db.commit()
        logger.info("✅ Phase 4 migrations completed successfully!")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info("✅ Created conversations table for session tracking")
        logger.info("✅ Created messages table for message history")
        logger.info("\n📋 Next steps:")
        logger.info("1. Update /ask endpoint to use conversation_id")
        logger.info("2. Frontend: pass conversation_id for follow-up questions")
        logger.info("3. Test query rewriting with follow-up questions")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_phase4_migrations()
