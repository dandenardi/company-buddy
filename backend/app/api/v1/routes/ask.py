from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.infrastructure.db.models.user_model import UserModel
from app.services.qdrant_service import QdrantService
from app.services.llm_service import LLMService

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AskResponse(BaseModel):
    answer: str
    context: list[str]


@router.post("", response_model=AskResponse)
def ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    question = payload.question

    if not question or question.strip() == "":
        raise HTTPException(status_code=400, detail="Pergunta inválida ou vazia.")

    # 1) Busca vetorial no Qdrant
    qdrant = QdrantService()
    results = qdrant.search(
        tenant_id=tenant_id,
        query_text=question,
        limit=payload.top_k,
    )

    context_chunks = [hit["text"] for hit in results]

    # 2) Chamar LLM com contexto
    llm = LLMService()
    answer = llm.answer_with_context(question, context_chunks)

    return AskResponse(answer=answer, context=context_chunks)
