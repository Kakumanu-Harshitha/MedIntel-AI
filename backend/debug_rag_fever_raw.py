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
    
    # Bypass the 0.3 threshold by calling index.query directly if needed, 
    # but let's first check what the actual service returns if we lower the threshold.
    
    # We'll use the raw index query to see everything
    index = rag_service.index
    from app.utils.embeddings_utils import embed_query
    q_vec = embed_query(query)
    
    if not q_vec:
        print("Failed to get query vector.")
        return

    results = index.query(vector=q_vec, top_k=10, include_metadata=True)
    
    print(f"\nRaw Results from Pinecone (top 10):")
    for i, match in enumerate(results.get("matches", [])):
        metadata = match.get("metadata", {})
        print(f"\n{i+1}. Score: {match['score']}")
        print(f"   Title: {metadata.get('title', 'N/A')}")
        print(f"   Source: {metadata.get('source', 'N/A')}")
        print(f"   Snippet: {metadata.get('text', '')[:150]}...")

if __name__ == "__main__":
    test_rag()
