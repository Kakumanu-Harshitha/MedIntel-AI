import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

def check_id():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX", "medical-memory"))
    
    doc_id = "common_cold"
    print(f"--- Fetching ID: {doc_id} ---")
    res = index.fetch(ids=[doc_id])
    
    vectors = res.get('vectors', {})
    if doc_id in vectors:
        print(f"✅ Found {doc_id}!")
        meta = vectors[doc_id]['metadata']
        print(f"Metadata Keys: {list(meta.keys())}")
        for k, v in meta.items():
            print(f"  {k}: {str(v)[:100]}")
    else:
        print(f"❌ {doc_id} NOT found in index.")

if __name__ == "__main__":
    check_id()
