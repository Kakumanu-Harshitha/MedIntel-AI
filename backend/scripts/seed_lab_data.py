import os
import json
import uuid
import sys
from dotenv import load_dotenv
from tqdm import tqdm

# Add project root to sys.path to import app modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from app.rag.rag_service import rag_service

# Load env from absolute path
load_dotenv(os.path.join(project_root, '.env'))

def seed_lab_data():
    """
    Seeds the lab reference dataset into Pinecone with new embeddings.
    """
    print("Starting Lab Reference Data Seeding...")
    
    if not rag_service.enabled:
        print("RAG Service is not enabled. Check PINECONE_API_KEY.")
        return

    json_path = os.path.join(os.path.dirname(__file__), '..', 'lab_reference_dataset.json')
    if not os.path.exists(json_path):
        print(f"Source file not found: {json_path}")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    # The dataset is a list of objects with text and metadata
    count = 0
    for entry in tqdm(data, desc="Indexing Lab Markers"):
        try:
            doc_id = entry.get("id") or str(uuid.uuid4())
            text = entry.get("text")
            metadata = entry.get("metadata", {})
            
            # Ensure mandatory fields for the routing logic
            metadata["dataset"] = "lab_reference"
            metadata["role"] = "LabExpert"
            
            if text:
                rag_service.upsert_document(
                    doc_id=doc_id,
                    text=text,
                    metadata=metadata,
                    namespace="lab_reference"
                )
                count += 1
        except Exception as e:
            print(f"Error indexing entry {entry.get('id')}: {e}")

    print(f"Lab Data Seeding Complete: {count} records indexed in 'lab_reference' namespace.")

if __name__ == "__main__":
    seed_lab_data()
