import os
import sys
from dotenv import load_dotenv

# Add app to path
sys.path.append(os.getcwd())
load_dotenv()

from app.rag.rag_service import rag_service

def test_rag():
    query = "fever"
    print(f"Testing RAG search for: {query}")
    results = rag_service.search(query, top_k=3)
    
    print(f"\nFound {len(results)} results:")
    for i, res in enumerate(results):
        print(f"\n{i+1}. [{res['source']}] {res['title']} (Score: {res['score']})")
        print(f"   Text: {res['text'][:300]}...")

if __name__ == "__main__":
    test_rag()
