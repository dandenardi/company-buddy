"""
Analytics API endpoints for RAG system metrics.

Provides aggregated metrics for:
- Overview (total queries, satisfaction, performance)
- Queries over time
- Satisfaction metrics
- Performance metrics
- Top documents
- Common questions
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.infrastructure.db.models.user_model import UserModel
from app.infrastructure.db.models.query_log_model import QueryLogModel
from app.infrastructure.db.models.feedback_model import FeedbackModel
from app.infrastructure.db.models.document_model import DocumentModel

router = APIRouter()


# Response Models
class OverviewMetrics(BaseModel):
    total_queries: int
    total_feedbacks: int
    satisfaction_rate: float  # 0-100
    avg_response_time_ms: float
    total_documents: int
    total_chunks: int


class QueryMetrics(BaseModel):
    date: str
    count: int


class SatisfactionMetrics(BaseModel):
    positive: int
    negative: int
    satisfaction_rate: float


class PerformanceMetrics(BaseModel):
    avg_response_time_ms: float
    avg_chunks_retrieved: float
    avg_score: float
    p50_response_time_ms: Optional[float] = None
    p95_response_time_ms: Optional[float] = None


class TopDocument(BaseModel):
    document_id: int
    document_name: str
    times_used: int


class CommonQuestion(BaseModel):
    question: str
    count: int
    avg_rating: Optional[float] = None


# Endpoints
@router.get("/overview", response_model=OverviewMetrics)
def get_overview(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get overview metrics for the last N days."""
    tenant_id = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)
    
    # Total queries
    total_queries = db.query(QueryLogModel).filter(
        QueryLogModel.tenant_id == tenant_id,
        QueryLogModel.created_at >= since
    ).count()
    
    # Total feedbacks
    total_feedbacks = db.query(FeedbackModel).filter(
        FeedbackModel.tenant_id == tenant_id,
        FeedbackModel.created_at >= since
    ).count()
    
    # Satisfaction rate
    feedbacks = db.query(FeedbackModel).filter(
        FeedbackModel.tenant_id == tenant_id,
        FeedbackModel.created_at >= since
    ).all()
    
    positive = sum(1 for f in feedbacks if f.rating == 5)
    satisfaction_rate = (positive / len(feedbacks) * 100) if feedbacks else 0
    
    # Avg response time
    avg_time = db.query(func.avg(QueryLogModel.response_time_ms)).filter(
        QueryLogModel.tenant_id == tenant_id,
        QueryLogModel.created_at >= since,
        QueryLogModel.response_time_ms.isnot(None)
    ).scalar() or 0
    
    # Total documents
    total_documents = db.query(DocumentModel).filter(
        DocumentModel.tenant_id == tenant_id
    ).count()
    
    # Total chunks (approximate from query logs)
    total_chunks = db.query(func.sum(QueryLogModel.chunks_retrieved)).filter(
        QueryLogModel.tenant_id == tenant_id,
        QueryLogModel.created_at >= since
    ).scalar() or 0
    
    return OverviewMetrics(
        total_queries=total_queries,
        total_feedbacks=total_feedbacks,
        satisfaction_rate=round(satisfaction_rate, 1),
        avg_response_time_ms=round(avg_time, 1),
        total_documents=total_documents,
        total_chunks=int(total_chunks) if total_chunks else 0,
    )


@router.get("/queries", response_model=List[QueryMetrics])
def get_queries_over_time(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get query count over time (daily aggregation)."""
    tenant_id = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)
    
    # Group by date
    results = db.query(
        func.date(QueryLogModel.created_at).label('date'),
        func.count(QueryLogModel.id).label('count')
    ).filter(
        QueryLogModel.tenant_id == tenant_id,
        QueryLogModel.created_at >= since
    ).group_by(
        func.date(QueryLogModel.created_at)
    ).order_by(
        func.date(QueryLogModel.created_at)
    ).all()
    
    return [
        QueryMetrics(date=str(r.date), count=r.count)
        for r in results
    ]


@router.get("/satisfaction", response_model=SatisfactionMetrics)
def get_satisfaction(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get satisfaction metrics."""
    tenant_id = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)
    
    feedbacks = db.query(FeedbackModel).filter(
        FeedbackModel.tenant_id == tenant_id,
        FeedbackModel.created_at >= since
    ).all()
    
    positive = sum(1 for f in feedbacks if f.rating == 5)
    negative = sum(1 for f in feedbacks if f.rating == 1)
    
    satisfaction_rate = (positive / len(feedbacks) * 100) if feedbacks else 0
    
    return SatisfactionMetrics(
        positive=positive,
        negative=negative,
        satisfaction_rate=round(satisfaction_rate, 1),
    )


@router.get("/performance", response_model=PerformanceMetrics)
def get_performance(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get performance metrics."""
    tenant_id = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)
    
    # Averages
    avg_time = db.query(func.avg(QueryLogModel.response_time_ms)).filter(
        QueryLogModel.tenant_id == tenant_id,
        QueryLogModel.created_at >= since,
        QueryLogModel.response_time_ms.isnot(None)
    ).scalar() or 0
    
    avg_chunks = db.query(func.avg(QueryLogModel.chunks_retrieved)).filter(
        QueryLogModel.tenant_id == tenant_id,
        QueryLogModel.created_at >= since
    ).scalar() or 0
    
    avg_score = db.query(func.avg(QueryLogModel.avg_score)).filter(
        QueryLogModel.tenant_id == tenant_id,
        QueryLogModel.created_at >= since,
        QueryLogModel.avg_score.isnot(None)
    ).scalar() or 0
    
    return PerformanceMetrics(
        avg_response_time_ms=round(avg_time, 1),
        avg_chunks_retrieved=round(avg_chunks, 1),
        avg_score=round(avg_score, 3),
    )


@router.get("/top-documents", response_model=List[TopDocument])
def get_top_documents(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get most recently uploaded documents."""
    tenant_id = current_user.tenant_id
    
    # Return top documents by upload date
    documents = db.query(DocumentModel).filter(
        DocumentModel.tenant_id == tenant_id
    ).order_by(
        DocumentModel.created_at.desc()
    ).limit(limit).all()
    
    return [
        TopDocument(
            document_id=doc.id,
            document_name=doc.original_filename,
            times_used=0  # TODO: Calculate from query_logs.chunks_used
        )
        for doc in documents
    ]


@router.get("/common-questions", response_model=List[CommonQuestion])
def get_common_questions(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Get most common questions."""
    tenant_id = current_user.tenant_id
    since = datetime.utcnow() - timedelta(days=days)
    
    # Group by question (case-insensitive)
    results = db.query(
        func.lower(QueryLogModel.question).label('question'),
        func.count(QueryLogModel.id).label('count')
    ).filter(
        QueryLogModel.tenant_id == tenant_id,
        QueryLogModel.created_at >= since
    ).group_by(
        func.lower(QueryLogModel.question)
    ).order_by(
        func.count(QueryLogModel.id).desc()
    ).limit(limit).all()
    
    return [
        CommonQuestion(question=r.question, count=r.count)
        for r in results
    ]
