from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from app.infrastructure.db.base import Base


class ConversationModel(Base):
    """
    Model for tracking conversation sessions.
    Each conversation has multiple messages (user + assistant turns).
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Auto-generated title from first question
    title = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("TenantModel")
    user = relationship("UserModel")
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")


class MessageModel(Base):
    """
    Model for individual messages within a conversation.
    Stores both user questions and assistant responses.
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    
    # Message role: "user" or "assistant"
    role = Column(String(20), nullable=False)
    
    # Message content
    content = Column(Text, nullable=False)
    
    # Metadata for assistant messages
    chunks_used = Column(JSON, nullable=True)  # Document IDs used
    rewritten_query = Column(Text, nullable=True)  # Standalone query (for user messages)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")
