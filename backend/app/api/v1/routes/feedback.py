from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import get_db, get_current_user
from app.infrastructure.db.models.user_model import UserModel
from app.infrastructure.db.models.feedback_model import FeedbackModel


router = APIRouter()


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: int  # 1 (👎) or 5 (👍)
    comment: Optional[str] = None
    chunks_used: Optional[list] = None
    avg_score: Optional[float] = None


class FeedbackResponse(BaseModel):
    status: str
    message: str


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> FeedbackResponse:
    """
    Submit user feedback on a RAG response.
    
    Rating values:
    - 1: Negative feedback (👎)
    - 5: Positive feedback (👍)
    """
    # Validate rating
    if payload.rating not in [1, 5]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be either 1 (negative) or 5 (positive)",
        )
    
    # Create feedback record
    feedback = FeedbackModel(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        question=payload.question,
        answer=payload.answer,
        rating=payload.rating,
        comment=payload.comment,
        chunks_used=payload.chunks_used,
        avg_score=payload.avg_score,
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return FeedbackResponse(
        status="success",
        message="Feedback submitted successfully. Thank you for helping us improve!",
    )


@router.get("/stats")
def get_feedback_stats(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get feedback statistics for the current tenant."""
    from sqlalchemy import func
    
    tenant_id = current_user.tenant_id
    
    # Total feedbacks
    total = db.query(func.count(FeedbackModel.id)).filter(
        FeedbackModel.tenant_id == tenant_id
    ).scalar()
    
    # Positive feedbacks
    positive = db.query(func.count(FeedbackModel.id)).filter(
        FeedbackModel.tenant_id == tenant_id,
        FeedbackModel.rating == 5,
    ).scalar()
    
    # Negative feedbacks
    negative = db.query(func.count(FeedbackModel.id)).filter(
        FeedbackModel.tenant_id == tenant_id,
        FeedbackModel.rating == 1,
    ).scalar()
    
    # Calculate satisfaction rate
    satisfaction_rate = (positive / total * 100) if total > 0 else 0
    
    return {
        "total_feedbacks": total,
        "positive": positive,
        "negative": negative,
        "satisfaction_rate": round(satisfaction_rate, 2),
    }
