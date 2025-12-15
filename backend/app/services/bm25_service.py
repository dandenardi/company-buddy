"""
BM25 Service for Lexical Search

This service provides keyword-based search using the BM25 algorithm.
It complements the vector search by finding exact matches for names, codes, and specific terms.

NOTE: Currently uses an in-memory index. In a production environment with multiple workers,
this should be replaced by a persistent solution (e.g., Redis, Elasticsearch, or Qdrant sparse vectors).
"""

import logging
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
import re

logger = logging.getLogger(__name__)

class BM25Service:
    """
    In-memory BM25 search service.
    """
    
    def __init__(self):
        self.corpus: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.metadata: List[Dict[str, Any]] = []
        self.bm25: BM25Okapi = None
        self._is_indexed = False
        
    def index_chunks(self, chunks_with_metadata: List[Dict[str, Any]]) -> None:
        """
        Index a list of chunks for BM25 search.
        
        Args:
            chunks_with_metadata: List of dicts containing 'text' and other metadata
        """
        if not chunks_with_metadata:
            logger.warning("[BM25] No chunks to index.")
            return
            
        logger.info(f"[BM25] Indexing {len(chunks_with_metadata)} chunks...")
        
        # Clear existing index (simplest approach for now)
        # In a real scenario, we might want to append or update
        self.corpus = [chunk["text"] for chunk in chunks_with_metadata]
        self.metadata = chunks_with_metadata
        
        # Simple tokenization: lowercase and split by non-alphanumeric
        self.tokenized_corpus = [self._tokenize(text) for text in self.corpus]
        
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        self._is_indexed = True
        
        logger.info("[BM25] Indexing complete.")
        
    def add_chunks(self, chunks_with_metadata: List[Dict[str, Any]]) -> None:
        """
        Add new chunks to the existing index.
        WARNING: This requires rebuilding the BM25 index which can be slow for large corpora.
        """
        if not chunks_with_metadata:
            return
            
        logger.info(f"[BM25] Adding {len(chunks_with_metadata)} chunks to index...")
        
        new_corpus = [chunk["text"] for chunk in chunks_with_metadata]
        new_tokenized = [self._tokenize(text) for text in new_corpus]
        
        self.corpus.extend(new_corpus)
        self.metadata.extend(chunks_with_metadata)
        self.tokenized_corpus.extend(new_tokenized)
        
        # Rebuild index
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        self._is_indexed = True
        
        logger.info(f"[BM25] Added chunks. Total corpus size: {len(self.corpus)}")

    def search(
        self, 
        query: str, 
        top_k: int = 10, 
        tenant_id: int | None = None
    ) -> List[Dict[str, Any]]:
        """
        Search corpus using BM25.
        
        Args:
            query: Search query
            top_k: Number of results to return
            tenant_id: Optional tenant_id to filter results (post-filtering)
            
        Returns:
            List of dicts with 'text', 'score', and metadata
        """
        if not self._is_indexed or not self.bm25:
            logger.warning("[BM25] Index is empty. Returning no results.")
            return []
            
        tokenized_query = self._tokenize(query)
        
        # Get scores for all documents
        scores = self.bm25.get_scores(tokenized_query)
        
        # Pair scores with metadata and sort
        results = []
        for i, score in enumerate(scores):
            # Apply tenant filter if provided
            if tenant_id is not None:
                doc_tenant = self.metadata[i].get("tenant_id")
                if doc_tenant is not None and doc_tenant != tenant_id:
                    continue
            
            if score > 0:
                result = self.metadata[i].copy()
                result["bm25_score"] = float(score)
                result["score"] = float(score) # Generic score field
                results.append(result)
                
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top K
        return results[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer."""
        # Lowercase and keep only alphanumeric chars
        text = text.lower()
        # Replace non-alphanumeric with space
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        return text.split()

# Singleton instance
_bm25_instance = None

def get_bm25_service() -> BM25Service:
    global _bm25_instance
    if _bm25_instance is None:
        _bm25_instance = BM25Service()
    return _bm25_instance
