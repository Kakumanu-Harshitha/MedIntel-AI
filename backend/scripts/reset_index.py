import os
import sys
from pinecone import Pinecone
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

def reset_medical_index():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "medical-memory")
    
    if not api_key:
        print("❌ Error: PINECONE_API_KEY not found in environment.")
        return

    print(f"Initializing Pinecone to reset index: {index_name}...")
    pc = Pinecone(api_key=api_key)
    
    if index_name not in pc.list_indexes().names():
        print(f"WARNING: Index {index_name} does not exist. Nothing to reset.")
        return

    index = pc.Index(index_name)
    
    # Check for --force flag
    import sys
    force = "--force" in sys.argv

    if not force:
        print(f"WARNING: This will delete ALL vectors in '{index_name}'.")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Reset cancelled.")
            return
    else:
        print(f"Force reset initiated for index: {index_name}")

    try:
        # Get stats to see namespaces
        stats = index.describe_index_stats()
        namespaces = stats.get('namespaces', {})
        
        for ns in namespaces:
            print(f"Deleting all vectors in namespace: '{ns}'...")
            index.delete(delete_all=True, namespace=ns)
        
        # Also try default namespace delete if it wasn't in stats (sometimes stats are delayed)
        if "" not in namespaces:
             print(f"Deleting all vectors in default namespace...")
             index.delete(delete_all=True)

        print(f"Reset complete for index: {index_name}")
    except Exception as e:
        print(f"Error resetting index: {e}")

if __name__ == "__main__":
    reset_medical_index()
