import json
import os
import time
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

try:
    from pinecone import Pinecone
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: Required libraries not installed.")
    print("Please run: pip install pinecone-client sentence-transformers python-dotenv")
    exit(1)

# --- CONFIGURATION ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX", "health-assistant-medical-knowledge")
NAMESPACE = "lab_reference"
EMBEDDING_MODEL_NAME = 'all-mpnet-base-v2'
DATASET_PATH = "lab_reference_dataset.json"

def get_embeddings(texts: List[str], model: SentenceTransformer) -> List[List[float]]:
    """Generates embeddings for a list of texts using sentence-transformers."""
    embeddings = model.encode(texts)
    return embeddings.tolist()

def upload_lab_data():
    """Main function to read, embed, and upload lab reference data."""
    
    if not PINECONE_API_KEY:
        print("Error: PINECONE_API_KEY must be set in environment variables.")
        return

    # Initialize Embedding Model
    print(f"⏳ Loading embedding model: {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print("✅ Model loaded.")

    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check if index exists
    existing_indexes = [i.name for i in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing_indexes:
        print(f"Error: Index '{PINECONE_INDEX_NAME}' not found.")
        print(f"Please ensure the index is created with dimension 768 for {EMBEDDING_MODEL_NAME}.")
        return

    index = pc.Index(PINECONE_INDEX_NAME)

    # Load Dataset
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset file '{DATASET_PATH}' not found.")
        return

    with open(DATASET_PATH, 'r') as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} documents from {DATASET_PATH}")

    # Prepare for Upsert (Batch processing)
    batch_size = 50
    total_batches = (len(dataset) + batch_size - 1) // batch_size

    for i in range(0, len(dataset), batch_size):
        batch = dataset[i : i + batch_size]
        texts = [doc['text'] for doc in batch]
        
        batch_num = i // batch_size + 1
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} docs)...")
        
        try:
            # Generate Embeddings
            embeddings = get_embeddings(texts, model)
            
            # Prepare Vectors
            vectors = []
            for doc, embedding in zip(batch, embeddings):
                # Ensure all metadata fields are present and correctly formatted
                metadata = {
                    "text": doc['text'],
                    "testKey": doc['metadata']['testKey'],
                    "testName": doc['metadata']['testName'],
                    "category": doc['metadata']['category'],
                    "aliases": doc['metadata']['aliases'],
                    "typicalUnits": doc['metadata']['typicalUnits'],
                    "sourceType": doc['metadata']['sourceType'],
                    "source": "Expert Lab Reference" # Adding source for priority routing
                }
                
                vectors.append({
                    "id": doc['id'],
                    "values": embedding,
                    "metadata": metadata
                })
            
            # Upsert to Pinecone
            index.upsert(vectors=vectors, namespace=NAMESPACE)
            print(f"✅ Successfully upserted batch {batch_num}")
            
        except Exception as e:
            print(f"❌ Error in batch {batch_num}: {e}")

    print("\n--- UPLOAD COMPLETE ---")
    print(f"Total documents processed: {len(dataset)}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Index: {PINECONE_INDEX_NAME}")

if __name__ == "__main__":
    upload_lab_data()
