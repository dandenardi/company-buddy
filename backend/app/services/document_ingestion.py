import logging
import os
from typing import List, Tuple, Dict, Any
import time
import hashlib

from fastapi import HTTPException
from sqlalchemy.orm import Session

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

        # 2) Semantic chunking with overlap and structure detection
        logger.info("[INGESTION] Gerando chunks semânticos...")
        
        chunker = get_semantic_chunker(
            max_chunk_size=1000,
            overlap_size=200,
        )
        
        doc_metadata = {
            "filename": document.original_filename,
            "category": getattr(document, "category", None),
        }
        
        chunks_with_metadata = chunker.chunk_text(raw_text, doc_metadata)
        logger.info(f"[INGESTION] Chunks gerados: {len(chunks_with_metadata)}")

        if not chunks_with_metadata:
            raise RuntimeError("Nenhum chunk gerado a partir do texto extraído.")
        
        # 3) Deduplication - check for existing hashes
        logger.info("[INGESTION] Verificando duplicatas...")
        existing_hashes = set(
            db.query(ChunkHashModel.content_hash)
            .filter(ChunkHashModel.tenant_id == document.tenant_id)
            .all()
        )
        existing_hashes = {h[0] for h in existing_hashes}
        
        # Filter out duplicates
        unique_chunks = []
        chunk_metadata_list = []
        duplicates_found = 0
        
        for chunk_text, chunk_meta in chunks_with_metadata:
            content_hash = chunk_meta["content_hash"]
            if content_hash not in existing_hashes:
                unique_chunks.append(chunk_text)
                chunk_metadata_list.append(chunk_meta)
                existing_hashes.add(content_hash)  # Track for this batch
            else:
                duplicates_found += 1
        
        logger.info(
            f"[INGESTION] Chunks únicos: {len(unique_chunks)}, "
            f"Duplicatas removidas: {duplicates_found}"
        )
        
        if not unique_chunks:
            logger.warning("[INGESTION] Todos os chunks são duplicatas. Nada a processar.")
            document.status = DocumentStatus.PROCESSED
            db.add(document)
            db.commit()
            return

        # 4) Generate embeddings
        logger.info("[INGESTION] Gerando embeddings com Gemini...")
        embedding_service = EmbeddingService()
        embeddings = embedding_service.embed_texts(unique_chunks)
        logger.info(f"[INGESTION] Embeddings gerados: {len(embeddings)}")

        # 5) Qdrant
        logger.info("[INGESTION] Enviando chunks para Qdrant...")
        qdrant_service = QdrantService()
        
        # Prepare metadata for Qdrant
        document_metadata = {
            "filename": document.original_filename,
            "category": getattr(document, "category", None),
            "content_type": document.content_type,
            "upload_date": document.created_at.isoformat() if document.created_at else None,
            "language": getattr(document, "language", "pt-BR"),
        }
        
        qdrant_service.upsert_chunks(
            tenant_id=document.tenant_id,
            document_id=document.id,
            chunks=unique_chunks,
            embeddings=embeddings,
            document_metadata=document_metadata,
        )
        logger.info("[INGESTION] Upsert no Qdrant concluído.")
        
        # 6) Save chunk hashes for deduplication
        logger.info("[INGESTION] Salvando hashes dos chunks...")
        for idx, (chunk_text, chunk_meta) in enumerate(zip(unique_chunks, chunk_metadata_list)):
            chunk_hash_record = ChunkHashModel(
                tenant_id=document.tenant_id,
                document_id=document.id,
                content_hash=chunk_meta["content_hash"],
                chunk_index=idx,
                char_count=chunk_meta.get("char_count"),
                word_count=chunk_meta.get("word_count"),
            )
            db.add(chunk_hash_record)
        
        db.commit()
        logger.info(f"[INGESTION] {len(unique_chunks)} hashes salvos.")

        # 7) Update document status
        document.status = DocumentStatus.PROCESSED
        if hasattr(document, "chunks_count"):
            document.chunks_count = len(unique_chunks)

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
