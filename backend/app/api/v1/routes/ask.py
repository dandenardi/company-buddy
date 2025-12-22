from __future__ import annotations

import time
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.config import settings
from app.infrastructure.db.models.user_model import UserModel
from app.infrastructure.db.models.tenant_model import TenantModel
from app.infrastructure.db.models.query_log_model import QueryLogModel
from app.infrastructure.db.models.conversation_model import ConversationModel, MessageModel

from app.services.llm_service import LLMService, LLMServiceError, get_llm_service
from app.services.qdrant_service import QdrantService
from app.services.query_rewriter import get_query_rewriter
from app.services.query_analyzer import get_query_analyzer
from app.services.hybrid_search_service import get_hybrid_search_service

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================
# Schemas
# ============================

class AskRequest(BaseModel):
    question: str
    conversation_id: int | None = None
    top_k: int = 5


class SourceChunk(BaseModel):
    text: str
    document_id: str | None = None
    document_name: str | None = None
    score: float | None = None
    cited: bool = False


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    has_answer: bool
    citations: List[int]
    conversation_id: int


# ============================
# Endpoint
# ============================

@router.post("", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    llm: LLMService = Depends(get_llm_service),
) -> AskResponse:
    start_time = time.time()

    tenant_id = current_user.tenant_id
    question = payload.question.strip()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pergunta inválida ou vazia.",
        )

    # =====================================================
    # 1. Conversa
    # =====================================================
    chat_history: list[dict] = []

    if payload.conversation_id:
        conversation = (
            db.query(ConversationModel)
            .filter(
                ConversationModel.id == payload.conversation_id,
                ConversationModel.tenant_id == tenant_id,
                ConversationModel.user_id == current_user.id,
            )
            .first()
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied.",
            )

        messages = (
            db.query(MessageModel)
            .filter(MessageModel.conversation_id == conversation.id)
            .order_by(MessageModel.created_at.asc())
            .limit(10)
            .all()
        )

        for msg in messages:
            chat_history.append({"role": msg.role, "content": msg.content})

    else:
        conversation = ConversationModel(
            tenant_id=tenant_id,
            user_id=current_user.id,
            title=question[:50],
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # =====================================================
    # 2. Rewrite de query
    # =====================================================
    search_query = question
    rewritten_query = None

    if chat_history:
        rewriter = get_query_rewriter(llm_service=llm)
        rewritten = rewriter.rewrite_with_context(question, chat_history)
        if rewritten != question:
            rewritten_query = rewritten
            search_query = rewritten

    # =====================================================
    # 3. Tenant prompt
    # =====================================================
    tenant: TenantModel | None = (
        db.query(TenantModel)
        .filter(TenantModel.id == tenant_id)
        .first()
    )

    tenant_prompt = tenant.custom_prompt if tenant and tenant.custom_prompt else None

    # =====================================================
    # 4. Adaptive K
    # =====================================================
    analyzer = get_query_analyzer()
    analysis = analyzer.analyze(search_query)

    if payload.top_k != 5:
        top_k = payload.top_k
    else:
        top_k = analysis["recommended_k"]

    # =====================================================
    # 5. Busca híbrida
    # =====================================================
    if settings.hybrid_search_enabled:
        hybrid = get_hybrid_search_service()
        results = hybrid.hybrid_search(
            tenant_id=tenant_id,
            query=search_query,
            top_k=top_k,
            vector_weight=settings.hybrid_vector_weight,
            bm25_weight=settings.hybrid_bm25_weight,
            rrf_k=settings.hybrid_rrf_k,
        )
    else:
        qdrant = QdrantService()
        results = qdrant.search(
            tenant_id=tenant_id,
            query_text=search_query,
            limit=top_k,
        )

    # =====================================================
    # 6. Montagem de contexto (1x apenas)
    # =====================================================
    context_chunks: list[Dict[str, Any]] = []
    sources: list[SourceChunk] = []

    for hit in results:
        text = hit.get("text") or hit.get("chunk_text") or ""
        if not text:
            continue

        chunk = {
            "text": text,
            "document_id": str(hit.get("document_id") or ""),
            "document_name": hit.get("document_name"),
            "score": hit.get("score"),
        }

        context_chunks.append(chunk)
        sources.append(
            SourceChunk(
                text=text,
                document_id=chunk["document_id"] or None,
                document_name=chunk["document_name"],
                score=chunk["score"],
            )
        )

    # =====================================================
    # 7. 🔒 Limite de contexto (RAM safe)
    # =====================================================
    MAX_CONTEXT_CHARS = 5_000

    total_chars = 0
    filtered_context = []
    filtered_sources = []

    for chunk, source in zip(context_chunks, sources):
        size = len(chunk["text"])
        if total_chars + size > MAX_CONTEXT_CHARS:
            break
        filtered_context.append(chunk)
        filtered_sources.append(source)
        total_chars += size

    context_chunks = filtered_context
    sources = filtered_sources

    logger.info(
        "[CONTEXT] chunks=%d chars=%d",
        len(context_chunks),
        total_chars,
    )

    # =====================================================
    # 8. LLM (executor)
    # =====================================================
    try:
        loop = asyncio.get_running_loop()

        def _call_llm():
            return llm.answer_with_context_and_citations(
                question=question,
                context_chunks=context_chunks,
                system_prompt=tenant_prompt,
                chat_history=chat_history,
            )

        result = await loop.run_in_executor(None, _call_llm)

        answer = result["answer"]
        citations = result["citations"]
        has_answer = result["has_answer"]

    except LLMServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception:
        logger.exception("Erro inesperado no /ask")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro inesperado ao processar a pergunta.",
        )

    # =====================================================
    # 9. Marca citações
    # =====================================================
    for c in citations:
        idx = c - 1
        if 0 <= idx < len(sources):
            sources[idx].cited = True

    # =====================================================
    # 10. Persistência
    # =====================================================
    db.add(
        MessageModel(
            conversation_id=conversation.id,
            role="user",
            content=question,
            rewritten_query=rewritten_query,
        )
    )

    db.add(
        MessageModel(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            chunks_used=[s.dict() for s in sources if s.cited],
        )
    )

    conversation.updated_at = datetime.utcnow()
    db.add(conversation)

    # =====================================================
    # 11. Observabilidade
    # =====================================================
    response_time_ms = int((time.time() - start_time) * 1000)

    scores = [s.score for s in sources if s.score is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    db.add(
        QueryLogModel(
            tenant_id=tenant_id,
            user_id=current_user.id,
            question=question,
            chunks_retrieved=len(results),
            avg_score=avg_score,
            response_time_ms=response_time_ms,
            conversation_id=conversation.id,
        )
    )

    db.commit()

    logger.info(
        "[ASK] tenant=%s conv=%s chunks=%s avg_score=%s time=%sms",
        tenant_id,
        conversation.id,
        len(results),
        f"{avg_score:.3f}" if avg_score else "n/a",
        response_time_ms,
    )

    return AskResponse(
        answer=answer,
        sources=sources,
        has_answer=has_answer,
        citations=citations,
        conversation_id=conversation.id,
    )
