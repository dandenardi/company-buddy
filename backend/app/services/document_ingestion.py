import os
from typing import List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.infrastructure.db.models.document_model import DocumentModel, DocumentStatus

from pypdf import PdfReader
from docx import Document as DocxDocument


def extract_text_from_pdf(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")
        return "\n".join(texts)
    except Exception as exc:
        raise RuntimeError(f"Erro ao extrair texto do PDF: {exc}")


def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = DocxDocument(file_path)
        texts = []
        for paragraph in doc.paragraphs:
            texts.append(paragraph.text)
        return "\n".join(texts)
    except Exception as exc:
        raise RuntimeError(f"Erro ao extrair texto do DOCX: {exc}")


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    """
    Chunk simples baseado em tamanho de caractere.
    Mais pra frente dá pra melhorar com divisão por parágrafos, sentenças, etc.
    """
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + max_chars, text_length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap  # volta um pouco pra garantir contexto
        if start < 0:
            start = 0

    return chunks


def run_document_ingestion(db: Session, document: DocumentModel) -> None:
    """
    Pipeline básica:
    - ler arquivo
    - extrair texto
    - chunkar
    - (placeholder) gerar embedding
    - (placeholder) enviar pro Qdrant
    - atualizar status
    """
    file_path = document.stored_filename

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=500,
            detail=f"Arquivo não encontrado para o documento {document.id}.",
        )

    # 1) extrair texto
    if document.content_type == "application/pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif document.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        raw_text = extract_text_from_docx(file_path)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não suportado para ingestão: {document.content_type}",
        )

    # 2) chunkar
    chunks = chunk_text(raw_text)

    # 👉 3) AQUI, depois, entra a parte de embeddings + Qdrant
    # ex:
    # vectors = embedding_service.embed(chunks)
    # qdrant_client.upsert(...)

    # 4) atualizar metadados
    document.status = DocumentStatus.PROCESSED
    document.chunks_count = len(chunks) if hasattr(document, "chunks_count") else None

    db.add(document)
    db.commit()
    db.refresh(document)
