from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from app.infrastructure.db.base import Base


class ChunkHashModel(Base):
    """
    Model for tracking chunk content hashes to enable deduplication.
    Prevents storing duplicate chunks across document versions.
    """
    __tablename__ = "chunk_hashes"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    # SHA256 hash of chunk content
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    # Metadata
    chunk_index = Column(Integer, nullable=False)  # Position in document
    char_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("TenantModel")
    document = relationship("DocumentModel")
    
    __table_args__ = (
        # Composite index for efficient lookups
        Index('idx_chunk_hash_tenant_doc', 'tenant_id', 'document_id'),
    )
