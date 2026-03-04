import os
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Global flags
RAG_ENABLED = False
_EMBEDDING_MODEL = None
PINECONE_INDEX = None

try:
    from pinecone import Pinecone, ServerlessSpec
    from sentence_transformers import SentenceTransformer
    
    def get_embedding_model():
        global _EMBEDDING_MODEL
        if _EMBEDDING_MODEL is None:
            print("⏳ Loading RAG Embedding Model (all-mpnet-base-v2)...")
            _EMBEDDING_MODEL = SentenceTransformer('all-mpnet-base-v2')
            print("✅ RAG Embedding Model loaded.")
        return _EMBEDDING_MODEL

    # --- COLD START FIX: Eagerly load model at import time ---
    # This prevents the 20–45s delay on the first real request.
    print("⏳ Pre-loading embedding model at startup...")
    get_embedding_model()
    print("✅ Embedding model pre-loaded.")

    # 2. Initialize Pinecone
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "health-assistant-medical-knowledge")
    
    if api_key:
        pc = Pinecone(api_key=api_key)
        
        # Check if index exists, if not create it
        existing_indexes = [i.name for i in pc.list_indexes()]
        if index_name not in existing_indexes:
            print(f"Creating Pinecone index: {index_name}...")
            pc.create_index(
                name=index_name,
                dimension=768, # Output dimension of all-mpnet-base-v2
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            time.sleep(2) # Wait for initialization
            
        PINECONE_INDEX = pc.Index(index_name)
        RAG_ENABLED = True
        print(f"✅ Pinecone Index '{index_name}' connected.")
    else:
        print("⚠️ PINECONE_API_KEY not found. Switching to MOCK RAG MODE (for demo).")
        RAG_ENABLED = True # Enable to show UI features

except ImportError:
    print("⚠️ Missing dependencies: 'pinecone' or 'sentence-transformers'. Run pip install.")
except Exception as e:
    print(f"❌ RAG Service Initialization Error: {e}")


class RAGService:
    def __init__(self):
        self.enabled = RAG_ENABLED
        self.index = PINECONE_INDEX
        self.mock_mode = (PINECONE_INDEX is None)

    @property
    def model(self):
        return get_embedding_model()

    def get_embedding(self, text: str) -> List[float]:
        model = self.model
        if not model:
            return []
        return model.encode(text).tolist()

    def upsert_document(self, doc_id: str, text: str, metadata: Dict[str, Any]):
        """
        Upserts a document into Pinecone.
        
        CRITICAL: For new datasets (WHO_NHS, SNOMED_CT, UMLS), the 'dataset' field is MANDATORY.
        This validation runs BEFORE checking if RAG is enabled to ensure data integrity.
        """
        # Validate mandatory 'dataset' field for new datasets (BEFORE enabled check)
        role = metadata.get('role', '')
        if role in ['PatientEducation', 'Taxonomy', 'SemanticMapping']:
            if 'dataset' not in metadata:
                raise ValueError(
                    f"CRITICAL: Missing required 'dataset' field for document '{doc_id}'. "
                    f"Role '{role}' requires dataset metadata for safe deletion. "
                    f"Expected values: 'WHO_NHS', 'SNOMED_CT', or 'UMLS'."
                )
            # Validate dataset value
            valid_datasets = ['WHO_NHS', 'SNOMED_CT', 'UMLS']
            if metadata['dataset'] not in valid_datasets:
                raise ValueError(
                    f"Invalid dataset value '{metadata['dataset']}' for document '{doc_id}'. "
                    f"Must be one of: {valid_datasets}"
                )
        
        if not self.enabled:
            return
            
        if self.mock_mode:
            print(f"  - [MOCK] Indexed: {metadata.get('title', doc_id)} [dataset={metadata.get('dataset', 'N/A')}]")
            return
        
        try:
            vector = self.get_embedding(text)
            self.index.upsert(vectors=[(doc_id, vector, metadata)])
        except Exception as e:
            print(f"❌ Upsert Error: {e}")

    def search(self, query: str, top_k: int = 5, namespace: str = None, filter: Dict = None) -> List[Dict[str, Any]]:
        """
        Retrieves relevant documents with hard-coded source priority ranking.
        Supports namespace filtering and metadata filters (e.g., testKey).
        """
        if not self.enabled:
            return []
            
        if self.mock_mode:
            print(f"🔍 [MOCK RAG] Returning trusted demo data for: {query[:30]}...")
            
            # SYMPTOM-AWARE MOCK RESPONSES
            query_lower = query.lower()
            
            # Check if this is a symptom query
            symptom_keywords = ["nausea", "headache", "bloating", "pain", "fever", "fatigue", 
                              "dizziness", "cough", "shortness of breath", "chest pain", 
                              "joint pain", "muscle ache", "diarrhea", "constipation", 
                              "insomnia", "rash", "symptom", "feel", "ache"]
            
            is_symptom_query = any(keyword in query_lower for keyword in symptom_keywords)
            
            if is_symptom_query:
                # Return symptom-focused mock data
                return [
                    {
                        "source": "MedlinePlus (NIH/NLM)", 
                        "title": "Symptom Information", 
                        "text": f"General information about common symptoms. Symptoms can have various causes ranging from minor issues to more serious conditions. Common causes include infections, inflammation, stress, dietary factors, or underlying health conditions. It's important to monitor symptoms and seek medical attention if they persist, worsen, or are accompanied by other concerning signs.",
                        "score": 0.95,
                        "category": "Primary Symptom",
                        "metadata": {"category": "Primary Symptom"}
                    },
                    {
                        "source": "MedlinePlus (NIH/NLM)", 
                        "title": "When to See a Doctor", 
                        "text": "You should consult a healthcare provider if symptoms are severe, persistent (lasting more than a few days), getting worse, or accompanied by other warning signs such as high fever, difficulty breathing, severe pain, or unusual changes in your body.",
                        "score": 0.90,
                        "category": "Patient Education",
                        "metadata": {"category": "Patient Education"}
                    }
                ]
            
            # Default disease/drug mock data for non-symptom queries
            return [
                {"source": "Drug Interaction", "title": "Interaction: Warfarin, Aspirin", "text": "Increased risk of bleeding. Both drugs have anticoagulant effects...", "score": 0.98, "metadata": {}},
                {"source": "MedlinePlus", "title": "Diabetes Overview", "text": "Diabetes is a disease in which your blood glucose levels are too high...", "score": 0.95, "metadata": {}},
                {"source": "ICD-11", "title": "ICD-11 Code: 5A11", "text": "Type 2 diabetes mellitus is characterized by insulin resistance...", "score": 0.90, "metadata": {}}
            ]
        
        try:
            # 1. Fetch more candidates than requested to allow for re-ranking
            fetch_k = max(top_k * 3, 15)
            query_vector = self.get_embedding(query)
            
            # Query with optional namespace and filter
            results = self.index.query(
                vector=query_vector,
                top_k=fetch_k,
                include_metadata=True,
                namespace=namespace,
                filter=filter
            )
            
            candidates = []
            for match in results['matches']:
                if match['score'] < 0.3:
                    continue
                
                source = match['metadata'].get('source', 'Unknown')
                candidates.append({
                    "text": match['metadata'].get('text', ''),
                    "source": source,
                    "title": match['metadata'].get('title', 'Untitled'),
                    "score": match['score'],
                    "category": match['metadata'].get('category', '')
                })

            # 2. Apply Hard-Coded Source Priority
            # Priority: 
            # 0. Primary Symptom (MedlinePlus) - Highest for symptom queries
            # 1. Drug Interaction (Safety)
            # 2. MedlinePlus & WHO/NHS (General Patient Education)
            # 3. ICD-11 (Taxonomy)
            # 4. PubMed (Research)
            # 5. Others
            def get_priority(doc):
                src = doc['source'].lower()
                cat = doc.get('category', '').lower()
                dataset = doc.get('metadata', {}).get('dataset', '').lower()
                
                if "primary symptom" in cat: return 0
                if "drug interaction" in src: return 1
                if "medlineplus" in src or dataset == "who_nhs": return 2
                if "icd-11" in src or "icd11" in src: return 3
                if "pubmed" in src: return 4
                return 5

            # Sort by priority first, then by semantic score
            candidates.sort(key=lambda x: (get_priority(x), -x['score']))

            # 3. Return top_k after re-ranking
            return candidates[:top_k]
            
        except Exception as e:
            print(f"❌ Search Error: {e}")
            return []

rag_service = RAGService()
