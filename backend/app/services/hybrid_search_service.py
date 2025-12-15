"""
Hybrid Search Service

Combines vector search (semantic) with BM25 search (lexical) using 
Reciprocal Rank Fusion (RRF) or Weighted Scoring.
"""

import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.services.qdrant_service import QdrantService
from app.services.reranker_service import get_reranker
from app.services.bm25_service import get_bm25_service

logger = logging.getLogger(__name__)

class HybridSearchService:
    def __init__(self):
        self.qdrant = QdrantService()
        self.bm25 = get_bm25_service()
        self.reranker = get_reranker()
        
    def hybrid_search(
        self,
        tenant_id: int,
        query: str,
        top_k: int = 5,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining Vector and BM25 results.
        Uses Reciprocal Rank Fusion (RRF) to combine the lists.
        Then applies Cross-Encoder Reranking for final result quality.
        """
        if not settings.hybrid_search_enabled:
            # Fallback to vector only if disabled
            return self.qdrant.search(tenant_id, query, limit=top_k)

        # 1. Broad Retrieval (Conceptually parallel)
        # Fetch MORE candidates than top_k to give Reranker more options
        initial_k = top_k * 4
        
        # Vector Search (Semantic)
        logger.info(f"[HYBRID] Running Vector search for '{query}'")
        vector_results = self.qdrant.search(
            tenant_id=tenant_id, 
            query_text=query, 
            limit=initial_k
        )
        
        # BM25 Search (Lexical)
        logger.info(f"[HYBRID] Running BM25 search for '{query}'")
        bm25_results = self.bm25.search(
            query=query, 
            top_k=initial_k,
            tenant_id=tenant_id
        )
        
        # 2. Apply Reciprocal Rank Fusion (RRF)
        fused_results = self._reciprocal_rank_fusion(
            vector_results, 
            bm25_results, 
            k=rrf_k,
            weights={'vector': vector_weight, 'bm25': bm25_weight}
        )
        
        # Take top N from fusion to send to reranker
        # (Fusion provides a good initial sorting, but Reranker refines it)
        candidates_for_reranking = fused_results[:initial_k]
        
        # 3. Apply Cross-Encoder Reranking
        logger.info(f"[HYBRID] Reranking {len(candidates_for_reranking)} candidates...")
        reranked_results = self.reranker.rerank(
            query=query,
            chunks=candidates_for_reranking,
            top_k=top_k
        )
        
        logger.info(
            f"[HYBRID] Search pipeline complete. "
            f"Vector: {len(vector_results)}, BM25: {len(bm25_results)} -> "
            f"Fused: {len(fused_results)} -> Reranked: {len(reranked_results)}"
        )
        
        return reranked_results

    def _reciprocal_rank_fusion(
        self,
        list_a: List[Dict[str, Any]],
        list_b: List[Dict[str, Any]],
        k: int = 60,
        weights: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Combine two lists of results using RRF.
        RRF Score = sum(weight * (1 / (k + rank)))
        """
        weights = weights or {'vector': 1.0, 'bm25': 1.0}
        
        # Map to verify uniqueness by ID (or text hash if ID not valid)
        # Using (document_id, chunk_index) or hash as unique key
        merged_scores = {}
        merged_docs = {}
        
        def get_unique_key(doc):
            # Prefer database ID ID/Chunk Index
            if 'document_id' in doc and 'chunk_index' in doc:
                return f"{doc['document_id']}_{doc['chunk_index']}"
            # Fallback to point ID from Qdrant
            if 'pk' in doc: 
                return str(doc['pk'])
            if 'id' in doc:
                return str(doc['id'])
            # Last resort: text hash (assuming text exists)
            return str(hash(doc.get('text', '')))

        # Process List A (Vector)
        for rank, doc in enumerate(list_a):
            key = get_unique_key(doc)
            score = weights['vector'] * (1 / (k + rank + 1))
            
            if key not in merged_scores:
                merged_scores[key] = 0.0
                doc_copy = doc.copy()
                doc_copy['source'] = 'vector' # debug info
                merged_docs[key] = doc_copy
                
            merged_scores[key] += score
            
        # Process List B (BM25)
        for rank, doc in enumerate(list_b):
            key = get_unique_key(doc)
            score = weights['bm25'] * (1 / (k + rank + 1))
            
            if key not in merged_scores:
                merged_scores[key] = 0.0
                doc_copy = doc.copy()
                doc_copy['source'] = 'bm25' # debug info
                merged_docs[key] = doc_copy
            else:
                # Mark as hybrid result
                merged_docs[key]['source'] = 'hybrid'
                
            merged_scores[key] += score

        # Sort by accumulated score
        sorted_keys = sorted(merged_scores.keys(), key=lambda x: merged_scores[x], reverse=True)
        
        final_list = []
        for key in sorted_keys:
            doc = merged_docs[key]
            doc['rrf_score'] = merged_scores[key]
            doc['score'] = merged_scores[key]  # Standardize score field
            final_list.append(doc)
            
        return final_list

# Singleton instance
_hybrid_service_instance = None

def get_hybrid_search_service() -> HybridSearchService:
    global _hybrid_service_instance
    if _hybrid_service_instance is None:
        _hybrid_service_instance = HybridSearchService()
    return _hybrid_service_instance
