# app/api/v1/routes/ask.py

from __future__ import annotations

import logging
import datetime as dt_module # Avoid conflict if any
from datetime import datetime
import logging
import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.infrastructure.db.models.user_model import UserModel
from app.infrastructure.db.models.tenant_model import TenantModel
from app.infrastructure.db.models.query_log_model import QueryLogModel
from app.services.qdrant_service import QdrantService
from app.services.llm_service import LLMService, LLMServiceError, get_llm_service
from app.services.query_rewriter import get_query_rewriter
from app.services.query_analyzer import get_query_analyzer
from app.infrastructure.db.models.conversation_model import ConversationModel, MessageModel

# ... (imports)



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
  has_answer: bool = True
  citations: List[int] = []
  conversation_id: int


router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("", response_model=AskResponse)
def ask(
  payload: AskRequest,
  db: Session = Depends(get_db),
  current_user: UserModel = Depends(get_current_user),
  llm: LLMService = Depends(get_llm_service),
) -> AskResponse:
  # Start timing for observability
  start_time = time.time()
  
  tenant_id = current_user.tenant_id
  question = payload.question

  if not question or question.strip() == "":
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Pergunta inválida ou vazia.",
    )

  # 1. Manage Conversation
  conversation = None
  chat_history = []
  
  if payload.conversation_id:
      conversation = (
          db.query(ConversationModel)
          .filter(
              ConversationModel.id == payload.conversation_id,
              ConversationModel.tenant_id == tenant_id,
              ConversationModel.user_id == current_user.id
          )
          .first()
      )
      
      if not conversation:
           raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="Conversation not found or access denied."
           )
      
      # Fetch recent history (last 10 messages)
      history_records = (
          db.query(MessageModel)
          .filter(MessageModel.conversation_id == conversation.id)
          .order_by(MessageModel.created_at.asc())
          .limit(10) # Limit context window
          .all()
      )
      
      for msg in history_records:
          chat_history.append({"role": msg.role, "content": msg.content})

  else:
      # Start new conversation
      # Title can be generated later or just use first 50 chars of query
      title = question[:50] + "..." if len(question) > 50 else question
      conversation = ConversationModel(
          tenant_id=tenant_id,
          user_id=current_user.id,
          title=title
      )
      db.add(conversation)
      db.commit()
      db.refresh(conversation)
  
  # 2. Query Rewriting
  search_query = question
  rewritten_query = None # To save in DB
  
  if chat_history:
      rewriter = get_query_rewriter(llm_service=llm)
      search_query = rewriter.rewrite_with_context(question, chat_history)
      if search_query != question:
          rewritten_query = search_query
          logger.info(f"[REWRITE] Original: '{question}' -> Rewritten: '{search_query}'")

  # 0) Busca o tenant para pegar o custom_prompt (se existir)
  tenant: TenantModel | None = (
    db.query(TenantModel)
    .filter(TenantModel.id == tenant_id)
    .first()
  )

  tenant_prompt = tenant.custom_prompt if tenant and tenant.custom_prompt else None

  # 0.5) Determinar K adaptativo baseado no tipo de pergunta
  # Note: Analyze the REWRITTEN query, as it contains the full intent
  analyzer = get_query_analyzer()
  query_analysis = analyzer.analyze(search_query)
  
  # Usar K adaptativo se o usuário não especificou um valor customizado
  user_specified_k = payload.top_k != 5  # 5 é o default
  if user_specified_k:
    top_k = payload.top_k
    logger.info(f"[ADAPTIVE_K] Using user-specified K={top_k}")
  else:
    top_k = query_analysis["recommended_k"]
    logger.info(
      f"[ADAPTIVE_K] Auto-adjusted K from 5 to {top_k} "
      f"(type={query_analysis['query_type']}, complexity={query_analysis['complexity_score']:.2f})"
    )

  # 1) Busca Híbrida (Vetorial + BM25)
  from app.services.hybrid_search_service import get_hybrid_search_service
  from app.core.config import settings
  
  hybrid_service = get_hybrid_search_service()
  
  use_hybrid = settings.hybrid_search_enabled
  
  if use_hybrid:
      results = hybrid_service.hybrid_search(
          tenant_id=tenant_id,
          query=search_query, # Use search_query
          top_k=top_k,
          vector_weight=settings.hybrid_vector_weight,
          bm25_weight=settings.hybrid_bm25_weight,
          rrf_k=settings.hybrid_rrf_k
      )
  else:
      qdrant = QdrantService()
      results = qdrant.search(
        tenant_id=tenant_id,
        query_text=search_query, # Use search_query
        limit=top_k,
      )


  # Preparar chunks com metadata para o LLM
  from typing import Any, Dict
  context_chunks_with_metadata: List[Dict[str, Any]] = []
  sources: List[SourceChunk] = []

  for hit in results:
    text = (
      hit.get("text")
      or hit.get("chunk_text")
      or hit.get("chunk")
      or ""
    )
    if not text:
      continue

    chunk_dict = {
      "text": text,
      "document_name": hit.get("document_name") or hit.get("file_name") or hit.get("filename"),
      "document_id": str(hit.get("document_id") or hit.get("doc_id") or ""),
      "score": hit.get("score"),
    }
    
    context_chunks_with_metadata.append(chunk_dict)

    sources.append(
      SourceChunk(
        text=text,
        document_id=chunk_dict["document_id"] or None,
        document_name=chunk_dict["document_name"],
        score=chunk_dict["score"],
        cited=False,  # Será atualizado depois
      )
    )

  if not context_chunks_with_metadata:
    logger.info("Nenhum chunk encontrado no Qdrant para tenant=%s", tenant_id)

  # 2) Chama o LLM com tratamento de erro e suporte a citações
  # Pass ORIGINAL question to LLM for tone, but retrieved chunks are from REWRITTEN
  try:
    result = llm.answer_with_context_and_citations(
      question=question, 
      context_chunks=context_chunks_with_metadata,
      system_prompt=tenant_prompt,
      chat_history=chat_history 
    )
    
    answer = result["answer"]
    citations = result["citations"]
    has_answer = result["has_answer"]
    
  except LLMServiceError as error:
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=str(error),
    ) from error
  except Exception as error:  # noqa: BLE001
    logger.exception("Erro inesperado ao processar /ask: %s", error)
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Erro inesperado ao processar sua pergunta.",
    ) from error
  
  # Marcar chunks citados
  for citation_num in citations:
    idx = citation_num - 1
    if 0 <= idx < len(sources):
      sources[idx].cited = True
  
  # 3. Persist Messages
  user_msg = MessageModel(
      conversation_id=conversation.id,
      role="user",
      content=question,
      rewritten_query=rewritten_query # Store rewrite
  )
  db.add(user_msg)
  
  assistant_msg = MessageModel(
      conversation_id=conversation.id,
      role="assistant",
      content=answer,
      chunks_used=[s.dict() for s in sources if s.cited] # Save citations
  )
  db.add(assistant_msg)
  
  # Update conversation updated_at
  conversation.updated_at = datetime.utcnow()
  db.add(conversation)
  db.commit()

  # 4) Log query for observability
  response_time_ms = int((time.time() - start_time) * 1000)
  
  # Calculate score statistics
  scores = [s.score for s in sources if s.score is not None]
  avg_score = sum(scores) / len(scores) if scores else None
  min_score = min(scores) if scores else None
  max_score = max(scores) if scores else None
  
  query_log = QueryLogModel(
    tenant_id=tenant_id,
    user_id=current_user.id,
    question=question,
    chunks_retrieved=len(results),
    chunks_used=[s.document_id for s in sources if s.document_id],
    avg_score=avg_score,
    min_score=min_score,
    max_score=max_score,
    response_time_ms=response_time_ms,
    conversation_id=conversation.id, # Link query log too
  )
  db.add(query_log)
  db.commit()
  
  logger.info(
    f"[ASK] tenant={tenant_id} conversation={conversation.id} chunks={len(results)} "
    f"avg_score={avg_score:.3f}" if avg_score else "avg_score=0.000",
    f" time={response_time_ms}ms"
  )

  return AskResponse(
    answer=answer,
    sources=sources,
    has_answer=has_answer,
    citations=citations,
    conversation_id=conversation.id,
  )
