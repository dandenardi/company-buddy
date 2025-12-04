from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON, Float
from sqlalchemy.orm import relationship
from app.infrastructure.db.base import Base


class FeedbackModel(Base):
    """
    Model for storing user feedback on RAG responses.
    Enables tracking of user satisfaction and quality metrics.
    """
    __tablename__ = "feedbacks"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Question and answer that were rated
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    
    # Rating: 1 (👎 negative) or 5 (👍 positive)
    rating = Column(Integer, nullable=False)
    
    # Optional user comment
    comment = Column(Text, nullable=True)
    
    # Metadata about the response
    chunks_used = Column(JSON, nullable=True)  # List of chunk IDs/document IDs used
    avg_score = Column(Float, nullable=True)  # Average relevance score of chunks
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("TenantModel")
    user = relationship("UserModel")
