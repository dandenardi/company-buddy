import logging
import os
from typing import List
import time

from fastapi import HTTPException
from sqlalchemy.orm import Session

from pypdf import PdfReader
from docx import Document as DocxDocument

from app.infrastructure.db.session import SessionLocal
from app.infrastructure.db.models.document_model import DocumentModel, DocumentStatus
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger("company_buddy.ingestion")

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


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    """
    Chunk simples baseado em palavras, sem overlap, focado em segurança.
    - Evita loops estranhos.
    - Garante que sempre termina.
    - Mesmo um texto gigante vira, no máximo, len(text)/max_chars chunks.
    """
    if not text:
        return []

    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for word in words:
        word_len = len(word) + 1  # +1 pelo espaço

        if current_length + word_len <= max_chars:
            current.append(word)
            current_length += word_len
        else:
            # fecha chunk atual
            if current:
                chunks.append(" ".join(current))
            # começa novo chunk com a palavra atual
            current = [word]
            current_length = word_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def _get_db_session() -> Session:
    return SessionLocal()


def run_document_ingestion(document_id: int) -> None:
    """
    Pipeline:

    - buscar document no banco
    - extrair texto do arquivo
    - chunkar
    - gerar embeddings
    - enviar pra Qdrant
    - atualizar status / chunks_count
    """
    db = SessionLocal()
    start_time = time.perf_counter()

    logger.info(f"[INGESTION] Iniciando ingestão do documento {document_id}")

    try:
        document: DocumentModel | None = (
            db.query(DocumentModel)
            .filter(DocumentModel.id == document_id)
            .first()
        )

        if document is None:
            logger.warning(f"[INGESTION] Documento {document_id} não encontrado no banco.")
            return

        logger.info(
            f"[INGESTION] Documento {document.id} (tenant={document.tenant_id}) "
            f"status_atual={document.status} tipo={document.content_type}"
        )

        file_path = document.stored_filename
        logger.info(f"[INGESTION] Caminho do arquivo: {file_path}")

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=500,
                detail=f"Arquivo não encontrado para o documento {document.id}.",
            )

        # 1) extrair texto
        logger.info("[INGESTION] Extraindo texto...")
        if document.content_type == "application/pdf":
            raw_text = extract_text_from_pdf(file_path)
        elif (
            document.content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            raw_text = extract_text_from_docx(file_path)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de arquivo não suportado para ingestão: {document.content_type}",
            )

        if not raw_text or not raw_text.strip():
            logger.warning(f"[INGESTION] Texto extraído vazio ou apenas whitespace. Tamanho={len(raw_text)}")
            raise RuntimeError("O arquivo não contém texto extraível (pode ser uma imagem ou estar vazio).")

        logger.info(f"[INGESTION] Texto extraído. Tamanho (chars)={len(raw_text)}")

        # 2) chunkar
        logger.info("[INGESTION] Gerando chunks...")
        chunks = chunk_text(raw_text)
        logger.info(f"[INGESTION] Chunks gerados: {len(chunks)}")

        if not chunks:
            raise RuntimeError("Nenhum chunk gerado a partir do texto extraído.")

        # 3) embeddings
        logger.info("[INGESTION] Gerando embeddings com Gemini...")
        embedding_service = EmbeddingService()
        embeddings = embedding_service.embed_texts(chunks)
        logger.info(f"[INGESTION] Embeddings gerados: {len(embeddings)}")

        # 4) Qdrant
        logger.info("[INGESTION] Enviando chunks para Qdrant...")
        qdrant_service = QdrantService()
        qdrant_service.upsert_chunks(
            tenant_id=document.tenant_id,
            document_id=document.id,
            chunks=chunks,
            embeddings=embeddings,
        )
        logger.info("[INGESTION] Upsert no Qdrant concluído.")

        # 5) atualizar status
        document.status = DocumentStatus.PROCESSED
        if hasattr(document, "chunks_count"):
            document.chunks_count = len(chunks)

        db.add(document)
        db.commit()
        db.refresh(document)

        elapsed = time.perf_counter() - start_time
        logger.info(
            f"[INGESTION] Documento {document.id} processado com sucesso. "
            f"Chunks={len(chunks)} tempo={elapsed:.2f}s"
        )

    except Exception as exc:
        # Marca como FAILED
        logger.exception(f"[INGESTION ERROR] Falha ao processar documento {document_id}: {exc}")

        document = (
            db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        )
        if document:
            document.status = DocumentStatus.FAILED
            if hasattr(document, "chunks_count"):
                document.chunks_count = None
            db.add(document)
            db.commit()
            logger.info(f"[INGESTION] Documento {document.id} marcado como FAILED.")
    finally:
        db.close()
        logger.info(f"[INGESTION] Encerrando ingestão do documento {document_id}")
