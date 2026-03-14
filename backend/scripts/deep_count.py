import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

def deep_count():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX", "medical-memory"))
    
    datasets = [
        "lab_reference",
        "MedlinePlus",
        "PubMed",
        "WHO_NHS",
        "ICD11_MMS",
        "OpenFDA_DDI",
        "common_diseases"
    ]
    
    print("--- Deep Metadata Count ---")
    for ds in datasets:
        # We can't actually 'count' without list or query
        # But we can query with a high top_k to see if we get more than 1
        res = index.query(
            vector=[0.0] * 768,
            filter={"dataset": ds},
            top_k=10000, 
            include_metadata=False
        )
        matches = res.get('matches', [])
        print(f"Dataset '{ds}': {len(matches)} records found in query.")

if __name__ == "__main__":
    deep_count()
