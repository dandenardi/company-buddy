# app/api/v1/routes/ask.py

from __future__ import annotations

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

router = APIRouter()
logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
  question: str
  top_k: int = 5


class SourceChunk(BaseModel):
  text: str
  document_id: str | None = None
  document_name: str | None = None
  score: float | None = None


class AskResponse(BaseModel):
  answer: str
  sources: List[SourceChunk]


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

  # 0) Busca o tenant para pegar o custom_prompt (se existir)
  tenant: TenantModel | None = (
    db.query(TenantModel)
    .filter(TenantModel.id == tenant_id)
    .first()
  )

  tenant_prompt = tenant.custom_prompt if tenant and tenant.custom_prompt else None

  # 1) Busca vetorial no Qdrant
  qdrant = QdrantService()
  # Aqui assumo que o search retorna uma lista de dicts com pelo menos "text"
  results = qdrant.search(
    tenant_id=tenant_id,
    query_text=question,
    limit=payload.top_k,
  )

  context_chunks: List[str] = []
  sources: List[SourceChunk] = []

  for hit in results:
    # defensivo: tenta vários nomes de campos
    text = (
      hit.get("text")
      or hit.get("chunk_text")
      or hit.get("chunk")
      or ""
    )
    if not text:
      continue

    context_chunks.append(text)

    sources.append(
      SourceChunk(
        text=text,
        document_id=str(
          hit.get("document_id")
          or hit.get("doc_id")
          or hit.get("documentId")
          or ""
        )
        or None,
        document_name=(
          hit.get("document_name")
          or hit.get("file_name")
          or hit.get("filename")
        ),
        score=hit.get("score"),
      )
    )

  if not context_chunks:
    # Não achou nada na base – ainda assim chamamos o LLM com "nenhum contexto"
    logger.info("Nenhum chunk encontrado no Qdrant para tenant=%s", tenant_id)

  # 2) Chama o LLM com tratamento de erro
  try:
    answer = llm.answer_with_context(
      question=question,
      context_chunks=context_chunks,
      system_prompt=tenant_prompt,  # <- aqui entra o prompt customizado do tenant
    )
  except LLMServiceError as error:
    # Erro esperado do LLM: retornamos 502 pro front com mensagem amigável
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=str(error),
    ) from error
  except Exception as error:  # noqa: BLE001
    # Erro inesperado mesmo
    logger.exception("Erro inesperado ao processar /ask: %s", error)
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Erro inesperado ao processar sua pergunta.",
    ) from error

  # 3) Log query for observability
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
  )
  db.add(query_log)
  db.commit()
  
  logger.info(
    f"[ASK] tenant={tenant_id} chunks={len(results)} "
    f"avg_score={avg_score:.3f if avg_score else 0} time={response_time_ms}ms"
  )

  return AskResponse(
    answer=answer,
    sources=sources,
  )
