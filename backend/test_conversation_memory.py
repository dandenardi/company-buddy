import sys
import os
from unittest.mock import MagicMock, patch

# Adiciona o diretório raiz
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.v1.routes.ask import ask, AskRequest
from app.infrastructure.db.models.conversation_model import ConversationModel, MessageModel

def test_conversation_flow():
    print("Testing Conversation Memory...")
    
    # Mock dependencies
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.tenant_id = 1
    mock_user.id = 1
    
    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.answer_with_context_and_citations.return_value = {
        "answer": "This is a mock answer",
        "citations": [],
        "has_answer": True
    }
    
    # Mock Services
    with patch("app.api.v1.routes.ask.get_query_analyzer") as mock_analyzer, \
         patch("app.api.v1.routes.ask.QdrantService") as mock_qdrant, \
         patch("app.services.hybrid_search_service.get_hybrid_search_service"):
         
        mock_analyzer.return_value.analyze.return_value = {
            "recommended_k": 3, 
            "query_type": "simple",
            "complexity_score": 0.5
        }
        mock_qdrant.return_value.search.return_value = [] # No documents needed for memory test
        
        # Test 1: New Conversation
        print("\n[Test 1] Start New Conversation")
        req1 = AskRequest(question="Hello, who acts as user 1?")
        
        # Mock DB behavior for logic
        # First query checks for tenant (returns None or mock)
        # We need to capture the conversation add
        
        # Mock conversation query - return None so it creates new
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Intercept DB adds to capture the new conversation object
        created_objects = []
        def capture_add(obj):
            created_objects.append(obj)
            if isinstance(obj, ConversationModel):
                obj.id = 101 # Simulate DB ID
        mock_db.add.side_effect = capture_add
        
        resp1 = ask(payload=req1, db=mock_db, current_user=mock_user, llm=mock_llm)
        
        print(f"Response conversation_id: {resp1.conversation_id}")
        assert resp1.conversation_id == 101
        
        # Verify messages saved
        saved_messages = [obj for obj in created_objects if isinstance(obj, MessageModel)]
        assert len(saved_messages) == 2 # User + Assistant
        print(f"Messages saved: {len(saved_messages)}")
        assert saved_messages[0].role == "user"
        assert saved_messages[1].role == "assistant"
        
        # Test 2: Continue Conversation
        print("\n[Test 2] Continue Conversation (Follow-up)")
        req2 = AskRequest(question="And what is his role?", conversation_id=101)
        
        # Mock DB to return existing conversation
        mock_conv = ConversationModel(id=101, tenant_id=1, user_id=1)
        
        # We need query() to behave dynamically.
        # 1. Tenant check -> mock_tenant
        # 2. Conversation check -> mock_conv
        # 3. Message history -> [msg1, msg2]
        
        mock_msg1 = MessageModel(role="user", content="Hello...")
        mock_msg2 = MessageModel(role="assistant", content="Answer...")
        
        # A simple side effect for query chains is hard with simple Mocks.
        # Let's verify the LLM call args instead.
        
        # Reset adds capture
        created_objects.clear()
        
        # Setup specific return for conversation query
        # Filter is called with (Conversation.id == payload.id, ...)
        # We can mock the query chain.
        
        # Simulating complex DB mocks is fragile. 
        # Let's trust that if the code paths run, verification is implicitly checked by flow.
        # But we want to ensure `chat_history` is passed to LLM.
        
        # Let's adjust mocks:
        # We need `db.query(ConversationModel).filter(...).first()` -> returns mock_conv
        # We need `db.query(MessageModel).filter(...).all()` -> returns history
        
        def query_side_effect(model):
            m = MagicMock()
            if model == ConversationModel:
                m.filter.return_value.first.return_value = mock_conv
            elif model == MessageModel:
                m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_msg1, mock_msg2]
            else:
                m.filter.return_value.first.return_value = None # Tenant, etc
            return m
            
        mock_db.query.side_effect = query_side_effect
        
        resp2 = ask(payload=req2, db=mock_db, current_user=mock_user, llm=mock_llm)
        
        assert resp2.conversation_id == 101
        
        # Verify LLM call arguments contained history
        call_args = mock_llm.answer_with_context_and_citations.call_args
        kwargs = call_args.kwargs
        history = kwargs.get("chat_history")
        
        print(f"Chat History passed to LLM: {history}")
        assert history is not None
        assert len(history) == 2
        assert history[0]["role"] == "user"
        
        print("PASS: Conversation Memory Verified")

if __name__ == "__main__":
    test_conversation_flow()
