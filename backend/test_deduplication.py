import sys
import os
import hashlib
from io import BytesIO
from unittest.mock import MagicMock, patch

# Adiciona o diretório raiz
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import UploadFile
from app.api.v1.routes.documents import upload_document
from app.infrastructure.db.models.document_model import DocumentModel, DocumentStatus

def test_deduplication_logic():
    print("Testing Deduplication & Versioning Logic...")
    
    # Mock dependencies
    mock_db = MagicMock()
    mock_bg_tasks = MagicMock()
    mock_user = MagicMock()
    mock_user.tenant_id = 1
    mock_user.id = 1
    
    # Mock file inputs
    content_a = b"File content A"
    content_b = b"File content B (different)"
    
    hash_a = hashlib.sha256(content_a).hexdigest()
    
    # 1. Test Deduplication
    print("\n[Test 1] Deduplication: Same content should return existing doc")
    
    mock_existing_doc = DocumentModel(id=100, content_hash=hash_a, original_filename="doc.pdf", version=1)
    
    # Mock DB query filter().first() to return existing doc
    mock_db.query.return_value.filter.return_value.first.return_value = mock_existing_doc
    
    file_a = UploadFile(filename="doc.pdf", file=BytesIO(content_a), headers={"content-type": "application/pdf"})
    # file_a.content_type = "application/pdf" # Removed setter
    
    # Call function
    result = upload_document(
        background_tasks=mock_bg_tasks,
        file=file_a,
        db=mock_db,
        current_user=mock_user
    )
    
    print(f"Result ID: {result.id}")
    assert result.id == 100
    print("PASS: Returned existing document.")
    
    # 2. Test Versioning
    print("\n[Test 2] Versioning: New content, same name should increment version")
    
    # Reset mocks
    mock_db.reset_mock()
    # First query (hash check) returns None
    # Second query (max version) returns 5
    mock_db.query.return_value.filter.return_value.first.return_value = None 
    mock_db.query.return_value.filter.return_value.scalar.return_value = 5
    
    file_b = UploadFile(filename="doc.pdf", file=BytesIO(content_b), headers={"content-type": "application/pdf"}) # Same name, diff content
    # file_b.content_type = "application/pdf"
    
    # Mock DB add
    def capture_add(doc):
        print(f"Added doc with version: {doc.version}")
        doc.id = 200 # Simulate DB ID assignment
        
    mock_db.add.side_effect = capture_add
    
    with patch("os.makedirs"), patch("builtins.open", MagicMock()):
        result = upload_document(
            background_tasks=mock_bg_tasks,
            file=file_b,
            db=mock_db,
            current_user=mock_user
        )
    
    assert result.version == 6
    print("PASS: Version incremented to 6.")

if __name__ == "__main__":
    test_deduplication_logic()
