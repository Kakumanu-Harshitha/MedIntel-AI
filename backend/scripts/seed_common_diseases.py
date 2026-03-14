import os
import json
import uuid
import sys
from tqdm import tqdm
from dotenv import load_dotenv

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from app.rag.rag_service import rag_service

load_dotenv()

def seed_common_diseases():
    """
    Seeds the common diseases dataset into Pinecone.
    """
    print("Starting Common Diseases Data Seeding...")
    
    if not rag_service.enabled:
        print("RAG Service is not enabled. Check PINECONE_API_KEY.")
        return

    json_path = os.path.join(os.path.dirname(__file__), '..', 'common_diseases_dataset.json')
    if not os.path.exists(json_path):
        print(f"Source file not found: {json_path}")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    count = 0
    for entry in tqdm(data, desc="Indexing Common Diseases"):
        try:
            doc_id = entry.get("id") or str(uuid.uuid4())
            text = entry.get("text")
            metadata = entry.get("metadata", {})
            
            if text:
                rag_service.upsert_document(
                    doc_id=doc_id,
                    text=text,
                    metadata=metadata
                )
                count += 1
        except Exception as e:
            print(f"Error indexing entry {entry.get('id')}: {e}")

    print(f"Common Diseases Seeding Complete: {count} records indexed.")

if __name__ == "__main__":
    seed_common_diseases()
