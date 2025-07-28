import requests
import json
import time
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def print_result(result: Dict[str, Any], max_length: int = 200):
    """Print a search result in a formatted way"""
    print(f"Source: {result['source']}")
    print(f"Score: {result['score']:.4f} | Rank: {result['rank']}")
    sentence = result['sentence']
    if len(sentence) > max_length:
        sentence = sentence[:max_length] + "..."
    print(f"Text: {sentence}")
    print("-" * 80)

def test_health_and_info():
    """Test basic health and info endpoints"""
    print_section("HEALTH CHECK & API INFO")
    
    # Health check
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=30)
        print(f"Health Status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"Data loaded: {health_data.get('data_loaded', False)}")
            print(f"Total sentences: {health_data.get('total_sentences', 0)}")
            print(f"Total documents: {health_data.get('total_documents', 0)}")
            
            models_ready = health_data.get('models_ready', {})
            print("Models ready:")
            for model, status in models_ready.items():
                print(f"  {model}: {'✓' if status else '✗'}")
        else:
            print(f"Health check failed: {response.text}")
    except Exception as e:
        print(f"Health check error: {e}")
        return False
    
    # API Info
    try:
        response = requests.get(f"{BASE_URL}/", timeout=30)
        print(f"\nAPI Info Status: {response.status_code}")
        if response.status_code == 200:
            info = response.json()
            print(f"API Version: {info.get('message', 'Unknown')}")
            print(f"Status: {info.get('status', 'Unknown')}")
        else:
            print(f"API info failed: {response.text}")
    except Exception as e:
        print(f"API info error: {e}")
    
    return True

def test_statistics():
    """Test the statistics endpoint"""
    print_section("STATISTICS")
    
    try:
        response = requests.get(f"{BASE_URL}/stats", timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"Total sentences: {stats.get('total_sentences', 0)}")
            print(f"Total documents: {stats.get('total_documents', 0)}")
            
            # Document type distribution
            doc_counts = stats.get('document_type_counts', {})
            if doc_counts:
                print("\nDocument types:")
                for doc_type, count in doc_counts.items():
                    print(f"  {doc_type}: {count}")
            
            # Cache info
            cache_info = stats.get('cache_info', {})
            if cache_info:
                print(f"\nCache size: {cache_info.get('total_cache_size_mb', 0):.2f} MB")
                print(f"Cache enabled: {cache_info.get('cache_enabled', False)}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Statistics error: {e}")

def test_search_query(query: str, method: str = "faiss", top_k: int = 3):
    """Test a single search query"""
    print(f"\n📝 Query: {query}")
    print(f"   Method: {method} | Top-K: {top_k}")
    
    payload = {
        "query": query,
        "method": method,
        "top_k": top_k,
        "min_score": 0.1
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/search", json=payload, timeout=60)
        response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {response_time:.2f}ms")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            server_time = result.get('execution_time_ms', 0)
            total_results = result.get('total_results', 0)
            
            print(f"   Server time: {server_time:.2f}ms")
            print(f"   Total results: {total_results}")
            
            # Display results by method
            methods_to_show = []
            if method in ["tfidf", "both"] and result.get("tfidf_results"):
                methods_to_show.append(("TF-IDF", result["tfidf_results"]))
            if method in ["embedding", "both"] and result.get("embedding_results"):
                methods_to_show.append(("Embedding", result["embedding_results"]))
            if method in ["faiss", "both"] and result.get("faiss_results"):
                methods_to_show.append(("FAISS", result["faiss_results"]))
            
            for method_name, results in methods_to_show:
                print(f"\n   🔍 {method_name} Results:")
                if results:
                    for result_item in results[:2]:  # Show top 2 results
                        print(f"      #{result_item['rank']} ({result_item['source']}) - Score: {result_item['score']:.4f}")
                        text = result_item['sentence'][:150] + "..." if len(result_item['sentence']) > 150 else result_item['sentence']
                        print(f"      {text}")
                        print()
                else:
                    print("      No results found")
        else:
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"   Search error: {e}")

def test_search_queries():
    """Test multiple search queries with different methods"""
    print_section("SEARCH TESTS")
    
    test_queries = [
        ("계약 해지에 관한 판례를 알려줘", "faiss"),
        ("민사소송 절차는 어떻게 되나요?", "both"),
        ("손해배상 책임에 대해 설명해주세요", "tfidf"),
        ("부동산 매매계약의 효력", "faiss"),
        ("소멸시효 완성의 효과", "embedding"),
    ]
    
    for query, method in test_queries:
        test_search_query(query, method, top_k=3)

def test_performance():
    """Test API performance with concurrent requests"""
    print_section("PERFORMANCE TEST")
    
    query = "계약 해지 판례"
    num_requests = 5
    
    print(f"Testing {num_requests} consecutive requests...")
    
    total_time = 0
    successful_requests = 0
    
    for i in range(num_requests):
        try:
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/search",
                json={"query": query, "method": "faiss", "top_k": 5},
                timeout=30
            )
            request_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                successful_requests += 1
                total_time += request_time
                print(f"  Request {i+1}: {request_time:.2f}ms ✓")
            else:
                print(f"  Request {i+1}: Failed ({response.status_code}) ✗")
                
        except Exception as e:
            print(f"  Request {i+1}: Error - {e} ✗")
    
    if successful_requests > 0:
        avg_time = total_time / successful_requests
        print(f"\nResults:")
        print(f"  Successful requests: {successful_requests}/{num_requests}")
        print(f"  Average response time: {avg_time:.2f}ms")

def main():
    """Run all tests"""
    print("🚀 Starting Legal RAG API Tests")
    print(f"Target URL: {BASE_URL}")
    
    # Test basic functionality
    if not test_health_and_info():
        print("❌ Health check failed. Is the server running?")
        return
    
    test_statistics()
    test_search_queries()
    test_performance()
    
    print_section("TESTS COMPLETED")
    print("✅ All tests finished!")

if __name__ == "__main__":
    main()
