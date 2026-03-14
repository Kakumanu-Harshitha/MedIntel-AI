import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

load_dotenv()

from app.rag.rag_service import rag_service

def debug_search():
    query = "fever"
    print(f"Searching for: {query}")
    results = rag_service.search(query, top_k=5)
    
    print(f"\nFound {len(results)} results:")
    for i, res in enumerate(results):
        print(f"\n{i+1}. [{res['source']}] {res['title']} (Score: {res['score']})")
        print(f"   Text: {res['text'][:200]}...")

if __name__ == "__main__":
    debug_search()
