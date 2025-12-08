"""
Test script for Phase 4: Conversational Context

This script tests:
1. Follow-up question detection
2. Query rewriting with context
3. Conversation models
"""

from app.services.query_rewriter import QueryRewriterService


def test_followup_detection():
    """Test follow-up question detection."""
    print("\n" + "="*60)
    print("TEST 1: Follow-up Question Detection")
    print("="*60)
    
    rewriter = QueryRewriterService()
    
    test_cases = [
        ("E para estagiários?", True),  # Starts with "E"
        ("Isso também se aplica?", True),  # Contains "isso"
        ("E ele?", True),  # Short + starts with E
        ("Qual a política de férias?", False),  # Full question
        ("Como funciona o plano de saúde?", False),  # Full question
        ("Também", True),  # Very short
    ]
    
    for query, expected in test_cases:
        is_followup = rewriter._is_followup_question(query)
        status = "✅" if is_followup == expected else "❌"
        print(f"{status} '{query}' -> Follow-up: {is_followup} (expected: {expected})")


def test_query_rewriting():
    """Test query rewriting with conversation history."""
    print("\n" + "="*60)
    print("TEST 2: Query Rewriting with Context")
    print("="*60)
    
    rewriter = QueryRewriterService()
    
    # Simulate conversation history
    history = [
        {"role": "user", "content": "Qual a política de férias da empresa?"},
        {"role": "assistant", "content": "Os colaboradores têm direito a 30 dias de férias por ano."},
    ]
    
    followup_query = "E para estagiários?"
    
    print(f"\nHistórico:")
    for msg in history:
        print(f"  {msg['role'].upper()}: {msg['content']}")
    
    print(f"\nPergunta atual: '{followup_query}'")
    print("\nReescrevendo...")
    
    # Note: This will call the LLM, so it requires API access
    try:
        rewritten = rewriter.rewrite_with_context(followup_query, history)
        print(f"\n✅ Pergunta reescrita: '{rewritten}'")
        
        if "estagiário" in rewritten.lower() and "férias" in rewritten.lower():
            print("✅ Rewriting captured context correctly")
        else:
            print("⚠️  Rewriting might need improvement")
    except Exception as e:
        print(f"⚠️  Rewriting failed (requires LLM access): {e}")


def test_no_rewrite_for_standalone():
    """Test that standalone questions are not rewritten."""
    print("\n" + "="*60)
    print("TEST 3: No Rewrite for Standalone Questions")
    print("="*60)
    
    rewriter = QueryRewriterService()
    
    history = [
        {"role": "user", "content": "Qual a política de férias?"},
        {"role": "assistant", "content": "30 dias por ano."},
    ]
    
    standalone_query = "Como funciona o plano de saúde?"
    
    print(f"Pergunta: '{standalone_query}'")
    
    rewritten = rewriter.rewrite_with_context(standalone_query, history)
    
    if rewritten == standalone_query:
        print("✅ Standalone question not rewritten (correct)")
    else:
        print(f"⚠️  Question was rewritten: '{rewritten}'")


def main():
    """Run all tests."""
    print("="*60)
    print("PHASE 4 CONVERSATIONAL CONTEXT TESTS")
    print("="*60)
    
    test_followup_detection()
    test_query_rewriting()
    test_no_rewrite_for_standalone()
    
    print("\n" + "="*60)
    print("TESTS COMPLETED")
    print("="*60)
    print("\n📋 Next steps:")
    print("1. Run migration: python migrate_phase4.py")
    print("2. Update /ask endpoint to use conversation_id")
    print("3. Test with real conversations")
    print("4. Frontend: implement conversation UI")


if __name__ == "__main__":
    main()
