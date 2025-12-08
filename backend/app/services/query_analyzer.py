"""
Query Analysis Service for Phase 3

Analyzes queries to determine optimal retrieval parameters:
- Adaptive K (number of chunks to retrieve)
- Query type classification
- Complexity assessment
"""

import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """
    Analyzes queries to optimize retrieval parameters.
    """
    
    # Query type patterns
    SIMPLE_PATTERNS = [
        r"^(o que é|quem é|quando|onde|qual)",
        r"^(what is|who is|when|where|which)",
    ]
    
    COMPLEX_PATTERNS = [
        r"(compare|diferença|todos|liste|enumere)",
        r"(compare|difference|all|list|enumerate)",
    ]
    
    PROCEDURAL_PATTERNS = [
        r"(como|passo a passo|processo|procedimento)",
        r"(how|step by step|process|procedure)",
    ]
    
    def analyze(self, query: str) -> Dict[str, Any]:
        """
        Analyze query and return retrieval parameters.
        
        Returns:
            {
                "query_type": "simple" | "complex" | "procedural" | "general",
                "recommended_k": int,
                "complexity_score": float (0-1),
            }
        """
        query_lower = query.lower().strip()
        
        # Determine query type
        query_type = self._classify_query_type(query_lower)
        
        # Determine recommended K
        recommended_k = self._get_recommended_k(query_type, query_lower)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity(query_lower)
        
        result = {
            "query_type": query_type,
            "recommended_k": recommended_k,
            "complexity_score": complexity_score,
        }
        
        logger.info(
            f"[QUERY_ANALYZER] Type={query_type}, K={recommended_k}, "
            f"Complexity={complexity_score:.2f}"
        )
        
        return result
    
    def _classify_query_type(self, query: str) -> str:
        """Classify query into type categories."""
        # Check simple patterns
        for pattern in self.SIMPLE_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return "simple"
        
        # Check complex patterns
        for pattern in self.COMPLEX_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return "complex"
        
        # Check procedural patterns
        for pattern in self.PROCEDURAL_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return "procedural"
        
        return "general"
    
    def _get_recommended_k(self, query_type: str, query: str) -> int:
        """Get recommended K based on query type."""
        # Base K values
        k_map = {
            "simple": 3,      # Simple questions need fewer chunks
            "complex": 10,    # Complex questions need more context
            "procedural": 7,  # Procedural needs moderate amount
            "general": 5,     # Default
        }
        
        base_k = k_map.get(query_type, 5)
        
        # Adjust based on query length (longer queries = more context needed)
        word_count = len(query.split())
        if word_count > 15:
            base_k += 2
        elif word_count > 25:
            base_k += 4
        
        # Cap at reasonable maximum
        return min(base_k, 15)
    
    def _calculate_complexity(self, query: str) -> float:
        """
        Calculate query complexity score (0-1).
        Higher score = more complex query.
        """
        score = 0.0
        
        # Length factor
        word_count = len(query.split())
        if word_count > 10:
            score += 0.2
        if word_count > 20:
            score += 0.2
        
        # Multiple questions
        if query.count("?") > 1:
            score += 0.2
        
        # Conjunctions (and, or, but)
        conjunctions = len(re.findall(r'\b(e|ou|mas|and|or|but)\b', query, re.IGNORECASE))
        score += min(conjunctions * 0.1, 0.3)
        
        # Comparison words
        if re.search(r'(compare|diferença|versus|vs)', query, re.IGNORECASE):
            score += 0.2
        
        return min(score, 1.0)


# Singleton instance
_analyzer_instance = None


def get_query_analyzer() -> QueryAnalyzer:
    """Get or create query analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = QueryAnalyzer()
    return _analyzer_instance
