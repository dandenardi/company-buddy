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
from app.services.query_analyzer import get_query_analyzer

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
  cited: bool = False  # Indica se foi citado na resposta


class AskResponse(BaseModel):
  answer: str
  sources: List[SourceChunk]
  has_answer: bool = True  # False se resposta for "não sei"
  citations: List[int] = []  # Números citados [1, 2, 3]


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

  # 0.5) Determinar K adaptativo baseado no tipo de pergunta
  analyzer = get_query_analyzer()
  query_analysis = analyzer.analyze(question)
  
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

  # 1) Busca vetorial no Qdrant
  qdrant = QdrantService()
  # Aqui assumo que o search retorna uma lista de dicts com pelo menos "text"
  results = qdrant.search(
    tenant_id=tenant_id,
    query_text=question,
    limit=top_k,  # Usar K adaptativo
  )


  # Preparar chunks com metadata para o LLM
  from typing import Any, Dict
  context_chunks_with_metadata: List[Dict[str, Any]] = []
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
    # Não achou nada na base – ainda assim chamamos o LLM com "nenhum contexto"
    logger.info("Nenhum chunk encontrado no Qdrant para tenant=%s", tenant_id)

  # 2) Chama o LLM com tratamento de erro e suporte a citações
  try:
    result = llm.answer_with_context_and_citations(
      question=question,
      context_chunks=context_chunks_with_metadata,
      system_prompt=tenant_prompt,  # <- aqui entra o prompt customizado do tenant
    )
    
    answer = result["answer"]
    citations = result["citations"]
    has_answer = result["has_answer"]
    
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
  
  # Marcar chunks citados
  for citation_num in citations:
    # citation_num é 1-indexed, sources é 0-indexed
    idx = citation_num - 1
    if 0 <= idx < len(sources):
      sources[idx].cited = True

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
    has_answer=has_answer,
    citations=citations,
  )
