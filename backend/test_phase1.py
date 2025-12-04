"""
Test script for Phase 1: Observability Foundation

This script tests the new observability features:
1. Query logging
2. Feedback submission
3. Metadata in Qdrant chunks
4. Score tracking
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TOKEN = None  # Will be set after login


def login(email: str, password: str):
    """Login and get access token."""
    global TOKEN
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        TOKEN = response.json()["access_token"]
        print("✅ Login successful")
        return True
    else:
        print(f"❌ Login failed: {response.text}")
        return False


def test_ask_with_logging():
    """Test /ask endpoint with query logging."""
    print("\n" + "="*60)
    print("TEST 1: Ask endpoint with query logging")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.post(
        f"{BASE_URL}/ask",
        headers=headers,
        json={"question": "Qual é a política de férias?", "top_k": 5}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Query successful")
        print(f"   Answer: {data['answer'][:100]}...")
        print(f"   Sources: {len(data['sources'])} chunks")
        
        # Check if scores are present
        if data['sources']:
            first_source = data['sources'][0]
            if 'score' in first_source and first_source['score'] is not None:
                print(f"   ✅ Scores present: {first_source['score']:.3f}")
            else:
                print("   ⚠️  Scores not present in response")
            
            if 'document_name' in first_source:
                print(f"   ✅ Metadata present: {first_source['document_name']}")
            else:
                print("   ⚠️  Document metadata not present")
        
        return data
    else:
        print(f"❌ Query failed: {response.text}")
        return None


def test_feedback_submission(question: str, answer: str):
    """Test feedback submission."""
    print("\n" + "="*60)
    print("TEST 2: Feedback submission")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # Test positive feedback
    response = requests.post(
        f"{BASE_URL}/feedback",
        headers=headers,
        json={
            "question": question,
            "answer": answer,
            "rating": 5,
            "comment": "Great answer!",
            "avg_score": 0.85
        }
    )
    
    if response.status_code == 201:
        print("✅ Positive feedback submitted successfully")
    else:
        print(f"❌ Feedback submission failed: {response.text}")
    
    # Test negative feedback
    response = requests.post(
        f"{BASE_URL}/feedback",
        headers=headers,
        json={
            "question": question,
            "answer": answer,
            "rating": 1,
            "comment": "Not helpful",
        }
    )
    
    if response.status_code == 201:
        print("✅ Negative feedback submitted successfully")
    else:
        print(f"❌ Negative feedback submission failed: {response.text}")


def test_feedback_stats():
    """Test feedback statistics endpoint."""
    print("\n" + "="*60)
    print("TEST 3: Feedback statistics")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(
        f"{BASE_URL}/feedback/stats",
        headers=headers
    )
    
    if response.status_code == 200:
        stats = response.json()
        print("✅ Feedback stats retrieved")
        print(f"   Total feedbacks: {stats['total_feedbacks']}")
        print(f"   Positive: {stats['positive']}")
        print(f"   Negative: {stats['negative']}")
        print(f"   Satisfaction rate: {stats['satisfaction_rate']}%")
    else:
        print(f"❌ Stats retrieval failed: {response.text}")


def check_database_tables():
    """Check if new tables were created."""
    print("\n" + "="*60)
    print("TEST 4: Database tables check")
    print("="*60)
    
    print("⚠️  Manual check required:")
    print("   Run: psql -U <user> -d <database> -c \"\\dt\"")
    print("   Expected tables: feedbacks, query_logs")
    print("   Run: psql -U <user> -d <database> -c \"\\d documents\"")
    print("   Expected columns: category, language, content_hash, version")


def main():
    """Run all tests."""
    print("="*60)
    print("PHASE 1 OBSERVABILITY TESTS")
    print("="*60)
    
    # Login
    email = input("Enter your email: ")
    password = input("Enter your password: ")
    
    if not login(email, password):
        print("Cannot proceed without authentication")
        return
    
    # Run tests
    ask_result = test_ask_with_logging()
    
    if ask_result:
        test_feedback_submission(
            question="Qual é a política de férias?",
            answer=ask_result['answer']
        )
    
    test_feedback_stats()
    check_database_tables()
    
    print("\n" + "="*60)
    print("TESTS COMPLETED")
    print("="*60)
    print("\n📋 Next steps:")
    print("1. Check backend logs for query logging entries")
    print("2. Verify database tables were created")
    print("3. Check Qdrant payloads have rich metadata")
    print("4. Monitor query_logs table for performance metrics")


if __name__ == "__main__":
    main()
