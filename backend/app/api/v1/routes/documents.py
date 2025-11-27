from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
import logging
from pathlib import Path

from app.core.deps import get_db, get_current_user
from app.infrastructure.db.models.document_model import DocumentModel, DocumentStatus
from app.schemas.document import DocumentBase
from app.infrastructure.db.models.user_model import UserModel
from app.services.document_ingestion import run_document_ingestion
from app.services.qdrant_service import QdrantService

UPLOAD_ROOT_DIR = "uploaded_files"

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.get("/", response_model=List[DocumentBase])
def list_documents(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    logger.info(f"Listing documents for user_id={current_user.id} email={current_user.email} tenant_id={current_user.tenant_id}")
    query = (
        db.query(DocumentModel)
        .filter(DocumentModel.tenant_id == current_user.tenant_id)
        .order_by(DocumentModel.created_at.desc())
    )
    results = query.all()
    logger.info(f"Found {len(results)} documents for tenant_id={current_user.tenant_id}")
    return results


@router.post("/upload", response_model=DocumentBase, status_code=status.HTTP_201_CREATED)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    if file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas PDF e DOCX são suportados no momento.",
        )

    tenant_folder = os.path.join(UPLOAD_ROOT_DIR, f"tenant_{current_user.tenant_id}")
    os.makedirs(tenant_folder, exist_ok=True)

    extension = os.path.splitext(file.filename or "")[1]
    unique_name = f"{uuid.uuid4().hex}{extension}"
    stored_path = os.path.join(tenant_folder, unique_name)

    with open(stored_path, "wb") as out_file:
        out_file.write(file.file.read())

    document = DocumentModel(
        tenant_id=current_user.tenant_id,
        owner_id=current_user.id,
        original_filename=file.filename or unique_name,
        stored_filename=stored_path,
        stored_path=stored_path,
        content_type=file.content_type,
        status=DocumentStatus.PROCESSING,  # agora começa como PROCESSING
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # dispara ingestão em background, passando só o ID
    background_tasks.add_task(run_document_ingestion, document.id)

    return document

@router.post("/{document_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_document_ingestion(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    document = (
        db.query(DocumentModel)
        .filter(
            DocumentModel.id == document_id,
            DocumentModel.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # volta pra PROCESSING
    document.status = DocumentStatus.PROCESSING
    db.add(document)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(run_document_ingestion, document.id)

    return {"detail": "Ingestion requeued."}

@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Faz o download do arquivo original do documento,
    garantindo que pertence ao tenant do usuário atual.
    """
    document: DocumentModel | None = (
        db.query(DocumentModel)
        .filter(
            DocumentModel.id == document_id,
            DocumentModel.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )

    file_path = document.stored_path  # ou document.file_path / o campo que você usa
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo do documento não foi encontrado no servidor.",
        )

    media_type = document.content_type or "application/octet-stream"
    download_name = document.original_filename or Path(file_path).name

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=download_name,
    )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    document = (
        db.query(DocumentModel)
        .filter(
            DocumentModel.id == document_id,
            DocumentModel.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Remove arquivo físico, se ainda existir
    if document.stored_filename and os.path.exists(document.stored_filename):
        try:
            os.remove(document.stored_filename)
        except OSError:
            # logar warning se quiser, mas não falhar por isso
            pass

    # Remove pontos do Qdrant
    qdrant = QdrantService()
    qdrant.delete_document(
        tenant_id=document.tenant_id,
        document_id=document.id,
    )

    # Remove registro do banco
    db.delete(document)
    db.commit()

    return