import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

# Mock Environment Variables for Testing
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["QDRANT_API_KEY"] = "mock_key"
os.environ["OPENAI_API_KEY"] = "mock_key"
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"

from app.services.bm25_service import get_bm25_service
from app.services.hybrid_search_service import get_hybrid_search_service

from unittest.mock import MagicMock, patch

# Mock env vars
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["QDRANT_API_KEY"] = "mock_key"
os.environ["OPENAI_API_KEY"] = "mock_key"
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"

from app.services.bm25_service import get_bm25_service
from app.services.hybrid_search_service import get_hybrid_search_service

def test_hybrid_search():
    print("="*60)
    print("TESTING HYBRID SEARCH COMPONENT")
    print("="*60)

    # Patch get_reranker to avoid model load
    import app.services.hybrid_search_service
    mock_get_reranker = MagicMock()
    app.services.hybrid_search_service.get_reranker = mock_get_reranker
    mock_get_reranker.return_value = MagicMock() # The mock reranker instance
        
    # 1. Setup Mock Data
    print("\n[Step 1] Populating BM25 Index with mock data...")
    bm25 = get_bm25_service()
    
    mock_chunks = [
        # Factual documents (lexical strong)
        {
            "text": "O prazo para entrega do relatório fiscal CNPJ 12.345.678/0001-90 é dia 05/10.",
            "document_id": "doc_1", 
            "chunk_index": 0,
            "document_name": "fiscal_2025.pdf",
            "tenant_id": 1
        },
        {
            "text": "A funcionária Maria Silva foi promovida para Gerente de Vendas em Agosto.",
            "document_id": "doc_2", 
            "chunk_index": 0,
            "document_name": "rh_promocoes.pdf",
             "tenant_id": 1
        },
        # Semantic documents
        {
            "text": "Para solicitar férias, o colaborador deve preencher o formulário no portal interno com 30 dias de antecedência.",
            "document_id": "doc_3", 
            "chunk_index": 0,
            "document_name": "politica_ferias.pdf",
             "tenant_id": 1
        },
         {
            "text": "O reembolso de despesas de viagem deve ser submetido até o dia 5 do mês subsequente.",
            "document_id": "doc_4", 
            "chunk_index": 0,
            "document_name": "politica_reembolso.pdf",
             "tenant_id": 1
        }
    ]
    
    bm25.index_chunks(mock_chunks)
    print("[OK] Index populated.")

    # 2. Test Lexical Search (BM25 only)
    print("\n[Step 2] Testing pure BM25 search...")
    query_factual = "Maria Silva"
    results = bm25.search(query_factual, top_k=2)
    
    print(f"Query: '{query_factual}'")
    for r in results:
        print(f"   - {r['text'][:50]}... (Score: {r['score']:.4f})")
        
    if results and "Maria Silva" in results[0]['text']:
        print("[OK] BM25 found exact match.")
    else:
        print("[FAIL] BM25 failed to find exact match.")

    # 3. Test Hybrid Fusion logic (Mocking Vector results)
    print("\n[Step 3] Testing Hybrid Fusion Logic (RRF)...")
    hybrid = get_hybrid_search_service()
    
    # We will mock qdrant search to avoid needing real Qdrant connection for this unit test
    class MockQdrant:
        def search(self, tenant_id, query_text, limit=5):
            # Simulate "semantic" finding doc_3 for vacation query
            if "descanso" in query_text or "ferias" in query_text.lower() or "férias" in query_text.lower():
                 return [{
                    "text": "Para solicitar férias, o colaborador deve preencher o formulário no portal interno com 30 dias de antecedência.",
                    "document_id": "doc_3",
                    "chunk_index": 0,
                    "score": 0.89,
                    "payload": {}
                }]
            return []
            
    hybrid.qdrant = MockQdrant()
    
    # Query: "férias Maria Silva" (Mixed: semantic + lexical)
    # Vector should find "ferias" (doc_3)
    # BM25 should find "Maria Silva" (doc_2)
    # Hybrid should return BOTH
    
    query_mixed = "férias Maria Silva"
    print(f"Query: '{query_mixed}'")
    
    results = hybrid.hybrid_search(tenant_id=1, query=query_mixed, top_k=5)
    
    found_types = set()
    for r in results:
        doc_id = r.get('document_id')
        score = r.get('rrf_score', 0)
        source = r.get('source', 'unknown')
        print(f"   - Doc: {doc_id} | Source: {source} | RRF: {score:.4f} | Text: {r['text'][:40]}...")
        found_types.add(doc_id)
        
    if "doc_2" in found_types and "doc_3" in found_types:
        print("[OK] Hybrid search successfully fused results from both sources.")
    else:
        print("[WARN] Hybrid search might be missing sources. Check logic.")

    # 4. Test Reranking Integration
    print("\n[Step 4] Testing Reranking Integration...")
    
    # Mock Reranker to avoid loading heavy model
    class MockReranker:
        def rerank(self, query, chunks, top_k=5, score_threshold=0.0):
            print(f"   [MockReranker] Reranking {len(chunks)} chunks for query '{query}'")
            # Simply reverse the list to simulate reordering
            reversed_chunks = chunks[::-1]
            for i, chunk in enumerate(reversed_chunks):
                chunk['rerank_score'] = 0.99 - (i * 0.1) # Fake high score
            return reversed_chunks[:top_k]

    # Inject mock reranker
    hybrid.reranker = MockReranker()
    
    print(f"Query: '{query_mixed}'")
    results = hybrid.hybrid_search(tenant_id=1, query=query_mixed, top_k=3)
    
    for r in results:
        print(f"   - Doc: {r.get('document_id')} | Rerank Score: {r.get('rerank_score', 0):.4f} | RRF Score: {r.get('rrf_score', 0):.4f}")
        
    if results and "rerank_score" in results[0]:
        print("[OK] Reranking applied successfully.")
    else:
        print("[FAIL] Reranking logic (mock) not executed.")

if __name__ == "__main__":
    test_hybrid_search()
