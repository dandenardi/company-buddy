from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON, Float
from sqlalchemy.orm import relationship
from app.infrastructure.db.base import Base


class QueryLogModel(Base):
    """
    Model for logging all RAG queries for analytics and observability.
    Tracks performance, relevance, and usage patterns.
    """
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    
    # The question asked
    question = Column(Text, nullable=False)
    
    # Retrieval metrics
    chunks_retrieved = Column(Integer, nullable=False, default=0)
    chunks_used = Column(JSON, nullable=True)  # List of document IDs that were used
    avg_score = Column(Float, nullable=True)  # Average similarity score of retrieved chunks
    min_score = Column(Float, nullable=True)  # Minimum score (to track quality threshold)
    max_score = Column(Float, nullable=True)  # Maximum score
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)  # Total response time in milliseconds
    embedding_time_ms = Column(Integer, nullable=True)  # Time to generate query embedding
    retrieval_time_ms = Column(Integer, nullable=True)  # Time to retrieve from Qdrant
    llm_time_ms = Column(Integer, nullable=True)  # Time for LLM generation
    
    # Token usage (for cost tracking)
    tokens_used = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    tenant = relationship("TenantModel")
    user = relationship("UserModel")
