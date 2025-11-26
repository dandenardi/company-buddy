from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import os
import uuid

from app.core.deps import get_db, get_current_user
from app.infrastructure.db.models.document_model import DocumentModel, DocumentStatus
from app.schemas.document import DocumentBase
from app.infrastructure.db.models.user_model import UserModel  
UPLOAD_ROOT_DIR = "uploaded_files"  

router = APIRouter(tags=["documents"])


@router.get("/", response_model=List[DocumentBase])
def list_documents(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    query = (
        db.query(DocumentModel)
        .filter(DocumentModel.tenant_id == current_user.tenant_id)
        .order_by(DocumentModel.created_at.desc())
    )
    return query.all()


@router.post("/upload", response_model=DocumentBase, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    
    if file.content_type not in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas PDF e DOCX são suportados no momento.",
        )

    # garante pasta do tenant
    tenant_folder = os.path.join(UPLOAD_ROOT_DIR, f"tenant_{current_user.tenant_id}")
    os.makedirs(tenant_folder, exist_ok=True)

    # nome de arquivo seguro
    extension = os.path.splitext(file.filename or "")[1]
    unique_name = f"{uuid.uuid4().hex}{extension}"
    stored_path = os.path.join(tenant_folder, unique_name)

    # salva arquivo físico
    with open(stored_path, "wb") as out_file:
        out_file.write(file.file.read())

    # cria registro no banco
    document = DocumentModel(
        tenant_id=current_user.tenant_id,
        owner_id=current_user.id,
        original_filename=file.filename or unique_name,
        stored_filename=stored_path,
        content_type=file.content_type,
        status=DocumentStatus.PROCESSING,
    )

    db.add(document)
    db.commit()
    db.refresh(document)
    background_tasks.add_task(run_document_ingestion, db, document)
    
    return document
