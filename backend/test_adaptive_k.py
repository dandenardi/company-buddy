import sys
import os

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.query_analyzer import get_query_analyzer

def test_adaptive_k():
    analyzer = get_query_analyzer()

    print("========================================")
    print("TESTING DYNAMIC TOP-K (QueryAnalyzer)")
    print("========================================")

    test_cases = [
        # Simple queries (Expect K=3-5)
        {"query": "Quem é o CEO?", "type": "simple", "max_k": 5},
        {"query": "O que é a Company Buddy?", "type": "simple", "max_k": 5},
        
        # Complex queries (Expect higher K)
        {"query": "Compare a política de férias com a licença maternidade e explique as diferenças", "type": "complex", "min_k": 8},
        {"query": "Liste todos os benefícios disponíveis para estagiários e CLT", "type": "complex", "min_k": 8},
        
        # Procedural (Expect moderate K)
        {"query": "Como solicitar reembolso passo a passo?", "type": "procedural", "min_k": 7},
        
        # Long query (General but long)
        {"query": "Eu gostaria de saber exatamente como funciona o processo de avaliação de desempenho para funcionários que acabaram de entrar na empresa e se existe algum período de experiência específico.", "type": "general", "min_k": 7}
    ]

    for case in test_cases:
        query = case["query"]
        result = analyzer.analyze(query)
        k = result["recommended_k"]
        q_type = result["query_type"]
        complexity = result["complexity_score"]
        
        print(f"\nQuery: '{query}'")
        print(f" -> Type: {q_type} | K: {k} | Complexity: {complexity:.2f}")
        
        passed = True
        
        # Check K limits
        if "max_k" in case and k > case["max_k"]:
             print(f"[FAIL] K {k} > Max {case['max_k']}")
             passed = False
        elif "min_k" in case and k < case["min_k"]:
             print(f"[FAIL] K {k} < Min {case['min_k']}")
             passed = False
             
        if passed:
             print("[PASS]")

if __name__ == "__main__":
    test_adaptive_k()
