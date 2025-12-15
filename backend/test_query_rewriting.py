import sys
import os
from unittest.mock import MagicMock, patch

# Adiciona o diretório raiz
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.v1.routes.ask import ask, AskRequest, router
from app.infrastructure.db.models.conversation_model import ConversationModel, MessageModel

def test_rewriting_flow():
    print("Testing Query Rewriting...")
    
    # Mock dependencies
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.tenant_id = 1
    mock_user.id = 1
    
    mock_llm = MagicMock()
    mock_llm.answer_with_context_and_citations.return_value = {
        "answer": "Answer", "citations": [], "has_answer": True
    }
    
    # Mock Rewriter
    with patch("app.api.v1.routes.ask.get_query_rewriter") as mock_get_rewriter, \
         patch("app.api.v1.routes.ask.get_query_analyzer") as mock_analyzer, \
         patch("app.services.hybrid_search_service.get_hybrid_search_service") as mock_hybrid:
         
        mock_rewriter = MagicMock()
        mock_get_rewriter.return_value = mock_rewriter
        
        # Scenario: "And for interns?" -> Rewrites to "What is policy for interns?"
        mock_rewriter.rewrite_with_context.return_value = "What is policy for interns?"
        
        mock_analyzer.return_value.analyze.return_value = {"recommended_k": 3, "query_type": "simple", "complexity_score": 0.5}
        mock_hybrid.return_value.hybrid_search.return_value = []
        
        # Setup conversation
        req = AskRequest(question="And for interns?", conversation_id=101)
        mock_conv = ConversationModel(id=101, tenant_id=1, user_id=1)
        
        # DB Mocks
        def query_side_effect(model):
            m = MagicMock()
            if model == ConversationModel:
                m.filter.return_value.first.return_value = mock_conv
            elif model == MessageModel:
                # Return some history
                msg1 = MessageModel(role="user", content="Vacation policy?")
                m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [msg1]
            return m
        mock_db.query.side_effect = query_side_effect
        
        # Test
        ask(payload=req, db=mock_db, current_user=mock_user, llm=mock_llm)
        
        # Assertions
        # 1. Rewriter called?
        mock_rewriter.rewrite_with_context.assert_called_once()
        args, _ = mock_rewriter.rewrite_with_context.call_args
        print(f"Rewriter called with query: '{args[0]}'")
        assert args[0] == "And for interns?"
        
        # 2. Search called with rewritten query?
        mock_hybrid.return_value.hybrid_search.assert_called_once()
        search_args = mock_hybrid.return_value.hybrid_search.call_args.kwargs
        print(f"Search called with query: '{search_args['query']}'")
        assert search_args['query'] == "What is policy for interns?"
        
        print("PASS: Query Rewriting Verified")

if __name__ == "__main__":
    test_rewriting_flow()
