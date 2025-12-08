"""
Test script for Phase 3: Advanced Retrieval

This script tests:
1. Query analyzer (adaptive K)
2. Reranking with cross-encoder
3. Score thresholds
"""

from app.services.query_analyzer import QueryAnalyzer
from app.services.reranker_service import RerankerService


def test_query_analyzer():
    """Test query type classification and adaptive K."""
    print("\n" + "="*60)
    print("TEST 1: Query Analyzer - Adaptive K")
    print("="*60)
    
    analyzer = QueryAnalyzer()
    
    test_queries = [
        ("O que é RAG?", "simple", 3),
        ("Como implementar um sistema RAG?", "procedural", 7),
        ("Compare RAG naive com RAG avançado", "complex", 10),
        ("Qual a política de férias?", "simple", 3),
        ("Liste todos os benefícios oferecidos pela empresa", "complex", 10),
    ]
    
    for query, expected_type, expected_k_range in test_queries:
        result = analyzer.analyze(query)
        print(f"\nQuery: '{query}'")
        print(f"  Type: {result['query_type']} (expected: {expected_type})")
        print(f"  Recommended K: {result['recommended_k']}")
        print(f"  Complexity: {result['complexity_score']:.2f}")
        
        if result['query_type'] == expected_type:
            print("  ✅ Type classification correct")
        else:
            print(f"  ⚠️  Expected {expected_type}, got {result['query_type']}")


def test_reranker():
    """Test reranking with cross-encoder."""
    print("\n" + "="*60)
    print("TEST 2: Reranker - Cross-Encoder")
    print("="*60)
    
    reranker = RerankerService()
    
    query = "Qual a política de férias da empresa?"
    
    # Simulate chunks with varying relevance
    chunks = [
        {
            "text": "A empresa oferece vale transporte e vale refeição.",
            "score": 0.75,  # High vector score but low relevance
        },
        {
            "text": "Os colaboradores têm direito a 30 dias de férias por ano.",
            "score": 0.65,  # Lower vector score but high relevance
        },
        {
            "text": "O plano de saúde cobre consultas e exames.",
            "score": 0.70,  # Medium vector score, low relevance
        },
        {
            "text": "As férias podem ser divididas em até 3 períodos.",
            "score": 0.60,  # Low vector score but high relevance
        },
    ]
    
    print(f"\nQuery: '{query}'")
    print(f"\nBefore reranking (sorted by vector score):")
    for i, chunk in enumerate(sorted(chunks, key=lambda x: x['score'], reverse=True)):
        print(f"  {i+1}. Score={chunk['score']:.2f}: {chunk['text'][:50]}...")
    
    # Rerank
    reranked = reranker.rerank(query, chunks, top_k=4)
    
    print(f"\nAfter reranking (sorted by rerank score):")
    for i, chunk in enumerate(reranked):
        print(f"  {i+1}. Rerank={chunk['rerank_score']:.2f}, Vector={chunk['score']:.2f}")
        print(f"      {chunk['text'][:60]}...")
    
    # Check if most relevant chunks are now on top
    if reranked[0]['text'].startswith("Os colaboradores"):
        print("\n✅ Reranking working correctly - most relevant chunk on top")
    else:
        print("\n⚠️  Reranking might need tuning")


def test_score_threshold():
    """Test dynamic score threshold."""
    print("\n" + "="*60)
    print("TEST 3: Dynamic Score Threshold")
    print("="*60)
    
    reranker = RerankerService()
    
    # Simulate chunks with scores
    chunks = [
        {"text": "Chunk 1", "rerank_score": 0.9},
        {"text": "Chunk 2", "rerank_score": 0.7},
        {"text": "Chunk 3", "rerank_score": 0.5},
        {"text": "Chunk 4", "rerank_score": 0.3},
        {"text": "Chunk 5", "rerank_score": 0.1},
    ]
    
    # Calculate dynamic threshold (keep top 70%)
    threshold = reranker.get_dynamic_threshold(chunks, percentile=0.3)
    
    print(f"Chunk scores: {[c['rerank_score'] for c in chunks]}")
    print(f"Dynamic threshold (30th percentile): {threshold:.2f}")
    print(f"Chunks above threshold: {sum(1 for c in chunks if c['rerank_score'] >= threshold)}")
    
    if 0.2 <= threshold <= 0.4:
        print("✅ Dynamic threshold calculated correctly")
    else:
        print(f"⚠️  Unexpected threshold: {threshold}")


def main():
    """Run all tests."""
    print("="*60)
    print("PHASE 3 ADVANCED RETRIEVAL TESTS")
    print("="*60)
    
    test_query_analyzer()
    test_reranker()
    test_score_threshold()
    
    print("\n" + "="*60)
    print("TESTS COMPLETED")
    print("="*60)
    print("\n📋 Next steps:")
    print("1. Install dependencies: pip install sentence-transformers")
    print("2. Test with real queries via /ask endpoint")
    print("3. Monitor logs for query analysis and reranking")
    print("4. Adjust MIN_RERANK_SCORE based on feedback")


if __name__ == "__main__":
    main()
