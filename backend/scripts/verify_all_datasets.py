import os
import sys
from pinecone import Pinecone
from dotenv import load_dotenv

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_path)

load_dotenv()

def verify_all_datasets():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "medical-memory")
    
    if not api_key:
        print("❌ Error: PINECONE_API_KEY not found.")
        return

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    
    print(f"--- Pinecone Audit for Index: {index_name} ---")
    
    try:
        stats = index.describe_index_stats()
        total_vectors = stats.get('total_vector_count', 0)
        namespaces = stats.get('namespaces', {})
        
        print(f"Total Vectors: {total_vectors}")
        print("\nBreakdown by Namespace:")
        if not namespaces:
            print("  (No namespaces found in stats - possibly all in default namespace)")
        for ns, data in namespaces.items():
            count = data.get('vector_count', 0)
            print(f"  - '{ns or '[Default]'}': {count} vectors")
            
        print("\n--- Detailed Dataset Audit (Sampling) ---")
        
        datasets_to_check = [
            "lab_reference",
            "MedlinePlus",
            "PubMed",
            "WHO_NHS",
            "ICD11_MMS",
            "OpenFDA_DDI",
            "common_diseases"
        ]
        
        # In Pinecone serverless, queries with metadata filters might be slow to update
        # We also want to check if the records ARE there but just not being filtered
        
        for ds in datasets_to_check:
            # Try to fetch ANY record with this dataset filter
            res = index.query(
                vector=[0.0] * 768,
                filter={"dataset": ds},
                top_k=1,
                include_metadata=True
            )
            matches = res.get('matches', [])
            
            if matches:
                 print(f"✅ Dataset '{ds}': Found")
                 sample = matches[0]['metadata']
                 print(f"     Title: {sample.get('title', 'N/A')}")
                 print(f"     Text Length: {len(sample.get('text', ''))}")
            else:
                 print(f"⚠️  Dataset '{ds}': Not found via filter yet.")

        print("\n--- Raw Metadata Samples (Last 10 results regardless of filter) ---")
        res_raw = index.query(vector=[0.0] * 768, top_k=10, include_metadata=True)
        for i, m in enumerate(res_raw.get('matches', [])):
            meta = m.get('metadata', {})
            print(f"  {i+1}. DS: {meta.get('dataset', '???')}, Src: {meta.get('source', 'N/A')}, Title: {meta.get('title', 'N/A')[:40]}...")

        print(f"\nAudit complete. Total vectors reported: {total_vectors}")
        
    except Exception as e:
        print(f"❌ Audit Error: {e}")

if __name__ == "__main__":
    verify_all_datasets()
