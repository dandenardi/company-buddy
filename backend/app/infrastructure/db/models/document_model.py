from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from app.infrastructure.db.base import Base  # ajusta se o Base estiver em outro módulo
import enum


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Metadata fields for observability
    category = Column(String, nullable=True)  # "juridico", "rh", "tecnico", etc.
    language = Column(String, default="pt-BR", nullable=False)
    page_count = Column(Integer, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash for deduplication
    version = Column(Integer, default=1, nullable=False)
    chunks_count = Column(Integer, nullable=True)

    # relationships
    tenant = relationship("TenantModel", back_populates="documents")
    owner = relationship("UserModel", back_populates="documents")