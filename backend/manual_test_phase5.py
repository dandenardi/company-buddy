"""
Manual Test Example for Phase 5

This file shows how to test the citation functionality manually.
You can use this as a reference when testing via API or frontend.
"""

# Example 1: Test with curl (replace YOUR_TOKEN with actual token)
"""
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual é a política de férias?",
    "top_k": 5
  }'
"""

# Expected response structure:
EXPECTED_RESPONSE = {
    "answer": "A política de férias permite 30 dias por ano [1]...",
    "sources": [
        {
            "text": "A política de férias permite 30 dias...",
            "document_id": "123",
            "document_name": "manual_rh.pdf",
            "score": 0.85,
            "cited": True  # ✅ Should be True if cited
        },
        {
            "text": "Outro chunk...",
            "document_id": "124",
            "document_name": "outro.pdf",
            "score": 0.65,
            "cited": False  # ❌ Should be False if not cited
        }
    ],
    "has_answer": True,  # Should be True if answer found
    "citations": [1]  # List of citation numbers
}

# Example 2: Test "no answer" detection
"""
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual é a receita do bolo de chocolate?",
    "top_k": 5
  }'
"""

EXPECTED_NO_ANSWER = {
    "answer": "Não encontrei essa informação nos documentos disponíveis...",
    "sources": [...],
    "has_answer": False,  # ✅ Should be False
    "citations": []  # Should be empty or minimal
}

# What to verify:
"""
✅ Checklist:
1. Response includes citations like [1], [2] in the answer text
2. Field 'citations' contains list of numbers [1, 2]
3. Sources with cited=True match the citation numbers
4. Questions without answers return has_answer=False
5. "Não encontrei" appears in answer when no answer found
"""
