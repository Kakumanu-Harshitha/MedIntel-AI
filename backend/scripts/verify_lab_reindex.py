import os
import sys
from dotenv import load_dotenv

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_path)

# Load env from absolute path (project root)
project_root = os.path.abspath(os.path.join(backend_path, '..'))
load_dotenv(os.path.join(project_root, '.env'))

from app.rag.rag_service import rag_service

load_dotenv()

def verify():
    print("Searching for 'hemoglobin' in 'lab_reference' namespace...")
    results = rag_service.search("hemoglobin", top_k=1, namespace="lab_reference")
    
    if not results:
        print("❌ FAIL: No results found.")
        return

    result = results[0]
    print(f"Top Result Source: {result.get('source')}")
    print(f"Top Result Title: {result.get('title')}")
    
    text = result.get('text')
    if text:
        print(f"✅ SUCCESS: 'text' field found! Length: {len(text)} characters.")
        print(f"Snippet: {text[:100]}...")
    else:
        print("❌ FAIL: 'text' field is missing or empty in search results.")

if __name__ == "__main__":
    verify()
