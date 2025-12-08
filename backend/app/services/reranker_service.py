"""
Reranking Service for Phase 3

This service provides reranking of search results using cross-encoder models.
Cross-encoders are more accurate than bi-encoders for relevance scoring.
"""

import logging
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class RerankerService:
    """
    Reranks search results using a cross-encoder model for better relevance.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranker with cross-encoder model.
        
        Args:
            model_name: HuggingFace model name for cross-encoder
                Default: ms-marco-MiniLM-L-6-v2 (fast, multilingual support)
        """
        logger.info(f"[RERANKER] Loading cross-encoder model: {model_name}")
        self.model = CrossEncoder(model_name)
        logger.info("[RERANKER] Model loaded successfully")
    
    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks by relevance using cross-encoder.
        
        Args:
            query: User query
            chunks: List of chunk dicts with 'text' field
            top_k: Number of top results to return
            score_threshold: Minimum rerank score (filter low-quality results)
        
        Returns:
            Reranked chunks with 'rerank_score' added
        """
        if not chunks:
            return []
        
        # Prepare pairs for cross-encoder
        pairs = [(query, chunk.get("text", "")) for chunk in chunks]
        
        # Get rerank scores
        logger.info(f"[RERANKER] Reranking {len(chunks)} chunks...")
        scores = self.model.predict(pairs)
        
        # Add rerank scores to chunks
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)
        
        # Filter by threshold
        filtered_chunks = [
            chunk for chunk in chunks
            if chunk["rerank_score"] >= score_threshold
        ]
        
        # Sort by rerank score (descending)
        reranked = sorted(
            filtered_chunks,
            key=lambda x: x["rerank_score"],
            reverse=True
        )
        
        # Return top K
        result = reranked[:top_k]
        
        logger.info(
            f"[RERANKER] Returned {len(result)} chunks "
            f"(filtered {len(chunks) - len(filtered_chunks)} below threshold)"
        )
        
        return result
    
    def get_dynamic_threshold(
        self,
        chunks: List[Dict[str, Any]],
        percentile: float = 0.3,
    ) -> float:
        """
        Calculate dynamic score threshold based on score distribution.
        
        Args:
            chunks: Chunks with rerank_score
            percentile: Percentile for threshold (0.3 = keep top 70%)
        
        Returns:
            Score threshold value
        """
        if not chunks:
            return 0.0
        
        scores = [chunk.get("rerank_score", 0.0) for chunk in chunks]
        scores.sort()
        
        # Get score at percentile
        index = int(len(scores) * percentile)
        threshold = scores[index] if index < len(scores) else 0.0
        
        logger.info(f"[RERANKER] Dynamic threshold: {threshold:.3f}")
        
        return threshold


# Singleton instance
_reranker_instance = None


def get_reranker() -> RerankerService:
    """Get or create reranker instance (singleton)."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = RerankerService()
    return _reranker_instance
