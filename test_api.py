import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_api():
    """Test the Legal RAG API"""
    
    # Test health check
    print("=== Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    print("\n=== API Info ===")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Statistics ===")
    try:
        response = requests.get(f"{BASE_URL}/stats")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
    
    # Test search queries
    test_queries = [
        "계약 해지에 관한 판례를 알려줘",
        "민사소송 절차는 어떻게 되나요?",
        "손해배상 책임에 대해 설명해주세요"
    ]
    
    for query in test_queries:
        print(f"\n=== Query: {query} ===")
        
        # Test with both methods
        payload = {
            "query": query,
            "method": "both",
            "top_k": 3
        }
        
        try:
            response = requests.post(f"{BASE_URL}/search", json=payload)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                print("\n--- TF-IDF Results ---")
                if result.get("tfidf_results"):
                    for i, res in enumerate(result["tfidf_results"], 1):
                        print(f"{i}. ({res['source']}) Score: {res['score']:.4f}")
                        print(f"   {res['sentence'][:200]}...")
                        print()
                else:
                    print("No TF-IDF results")
                
                print("\n--- Embedding Results ---")
                if result.get("embedding_results"):
                    for i, res in enumerate(result["embedding_results"], 1):
                        print(f"{i}. ({res['source']}) Score: {res['score']:.4f}")
                        print(f"   {res['sentence'][:200]}...")
                        print()
                else:
                    print("No embedding results")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_api()