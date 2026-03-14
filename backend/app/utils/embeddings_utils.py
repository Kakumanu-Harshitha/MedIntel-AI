import os
from pinecone import Pinecone
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Initialize Pinecone client
api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=api_key) if api_key else None

def embed_query(text: str) -> List[float]:
    """
    Generates an embedding for a query using Pinecone's hosted inference.
    Model: llama-text-embed-v2 (768 dimensions)
    """
    if not pc:
        print("WARNING: Pinecone client not initialized in embeddings_utils. Check API key.")
        return []
        
    try:
        print(f"DEBUG: Generating embedding for text snippet: {text[:50]}...")
        response = pc.inference.embed(
            model="llama-text-embed-v2",
            inputs=[text],
            parameters={
                "input_type": "query",
                "dimension": 768
            }
        )
        # Handle both object and dict response formats
        emb = response.data[0].values if hasattr(response.data[0], "values") else response.data[0].get("values")
        if emb is None:
             print(f"ERROR: Could not find 'values' in Pinecone Inference response: {response.data[0]}")
             return []
        print(f"DEBUG: Generated embedding of length: {len(emb)}")
        return emb
    except Exception as e:
        print(f"ERROR: Pinecone Inference Error (query): {e}")
        return []

def embed_passage(text: str) -> List[float]:
    """
    Generates an embedding for a passage/document using Pinecone's hosted inference.
    Model: llama-text-embed-v2 (768 dimensions)
    """
    if not pc:
        print("WARNING: Pinecone client not initialized in embeddings_utils. Check API key.")
        return []
        
    try:
        print(f"DEBUG: Generating passage embedding for text snippet: {text[:50]}...")
        response = pc.inference.embed(
            model="llama-text-embed-v2",
            inputs=[text],
            parameters={
                "input_type": "passage",
                "dimension": 768
            }
        )
        # Handle both object and dict response formats
        emb = response.data[0].values if hasattr(response.data[0], "values") else response.data[0].get("values")
        if emb is None:
             print(f"ERROR: Could not find 'values' in Pinecone Inference response: {response.data[0]}")
             return []
        print(f"DEBUG: Generated passage embedding of length: {len(emb)}")
        return emb
    except Exception as e:
        print(f"ERROR: Pinecone Inference Error (passage): {e}")
        return []
