
import os
import sys
from dotenv import load_dotenv

# Add the current directory to sys.path to allow importing from the backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_service import rag_service
from rag_router import rag_router, QueryIntent

def test_rag_retrieval(query):
    print(f"\n--- Testing RAG Retrieval for: '{query}' ---")
    
    # 1. Detect Intent
    intent = rag_router.detect_intent(query)
    print(f"Detected Intent: {intent}")
    
    # 2. Augment Query
    augmented_query = rag_router.augment_query(query, intent)
    print(f"Augmented Query: {augmented_query}")
    
    # 3. Search
    results = rag_service.search(augmented_query, top_k=5)
    
    print(f"Results Found: {len(results)}")
    for i, res in enumerate(results):
        print(f"\nResult {i+1} (Score: {res['score']:.4f}):")
        print(f"Source: {res['source']}")
        print(f"Title: {res['title']}")
        print(f"Text Snippet: {res['text'][:200]}...")

if __name__ == "__main__":
    load_dotenv()
    test_rag_retrieval("What is Eczema?")
    test_rag_retrieval("I have itchy red patches on my skin")
    test_rag_retrieval("Dengue symptoms")
