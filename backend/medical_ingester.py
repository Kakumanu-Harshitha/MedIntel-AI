import os
import json
import hashlib
import re
import requests
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
from tqdm import tqdm
from pinecone import Pinecone, ServerlessSpec
from app.utils.embeddings_utils import embed_passage
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MedicalIngester:
    def __init__(self):
        # Configuration
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX", "medical-memory")
        self.model_name = "llama-text-embed-v2" # Hosted inference
        self.chunk_size = 800  # characters
        self.chunk_overlap = 100
        self.similarity_threshold = 0.95
        
        # Initialize components
        print(f"Using Pinecone hosted embeddings: {self.model_name}...")
        # No local model initialization needed
        
        print(f"Initializing Pinecone...")
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        
        # Ensure index exists
        if self.pinecone_index_name not in self.pc.list_indexes().names():
            print(f"Creating index {self.pinecone_index_name}...")
            self.pc.create_index(
                name=self.pinecone_index_name,
                dimension=768,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
        self.index = self.pc.Index(self.pinecone_index_name)
        
        # Tracking for report
        self.stats = {
            "total_pages_attempted": 0,
            "total_pages_ingested": 0,
            "total_chunks_processed": 0,
            "total_chunks_inserted": 0,
            "duplicates_skipped_url": 0,
            "duplicates_skipped_hash": 0,
            "duplicates_skipped_similarity": 0,
            "dataset_counts": {}
        }
        
        # Persistent URL tracking
        self.url_tracker_file = "ingested_urls.txt"
        self.ingested_urls = self._load_ingested_urls()

    def _load_ingested_urls(self) -> set:
        if os.path.exists(self.url_tracker_file):
            with open(self.url_tracker_file, "r") as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def _save_url(self, url: str):
        self.ingested_urls.add(url)
        with open(self.url_tracker_file, "a") as f:
            f.write(f"{url}\n")

    def _normalize_text(self, text: str) -> str:
        # Lowercase, remove extra whitespace, remove non-alphanumeric noise
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.\,\?\!]', '', text)
        return text.strip()

    def _compute_hash(self, text: str) -> str:
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _get_dataset_type(self, url: str) -> str:
        if "medlineplus.gov" in url: return "medlineplus"
        if "nhs.uk" in url: return "nhs"
        if "who.int" in url: return "who"
        return "other"

    def scrape_url(self, url: str) -> Optional[str]:
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Remove scripts, styles, nav, footer
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            # Extract main content based on source
            content = ""
            if "medlineplus.gov" in url:
                main = soup.find('div', id='maincontent') or soup.find('article')
                content = main.get_text(separator=' ') if main else soup.get_text(separator=' ')
            elif "nhs.uk" in url:
                main = soup.find('main') or soup.find('div', class_='nhsuk-width-container')
                content = main.get_text(separator=' ') if main else soup.get_text(separator=' ')
            elif "who.int" in url:
                main = soup.find('article') or soup.find('div', class_='sf-detail-body-wrapper')
                content = main.get_text(separator=' ') if main else soup.get_text(separator=' ')
            else:
                content = soup.get_text(separator=' ')
            
            return re.sub(r'\s+', ' ', content).strip()
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

    def chunk_text(self, text: str) -> List[str]:
        # Simple recursive-like chunking
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Look for sentence end or period
            last_period = text.rfind('.', start, end)
            if last_period != -1 and last_period > start + (self.chunk_size // 2):
                end = last_period + 1
            
            chunks.append(text[start:end].strip())
            start = end - self.chunk_overlap
        return chunks

    def check_duplicate_hash(self, chunk_hash: str) -> bool:
        try:
            # We use a zero vector for the query as we are filtering by metadata only
            results = self.index.query(
                vector=[0.0] * 768, 
                filter={"chunkHash": {"$eq": chunk_hash}},
                top_k=1,
                include_metadata=True
            )
            return len(results['matches']) > 0
        except:
            return False

    def check_similarity(self, embedding: List[float]) -> bool:
        try:
            results = self.index.query(
                vector=embedding,
                top_k=1,
                include_metadata=True
            )
            if results['matches'] and results['matches'][0]['score'] > self.similarity_threshold:
                return True
            return False
        except:
            return False

    def ingest(self, urls: List[str]):
        print(f"Starting ingestion of {len(urls)} URLs...")
        
        for url in tqdm(urls, desc="Processing URLs"):
            self.stats["total_pages_attempted"] += 1
            
            # Level 1 Dedup: URL
            if url in self.ingested_urls:
                # self.stats["duplicates_skipped_url"] += 1
                continue
            
            text = self.scrape_url(url)
            if not text or len(text) < 200:
                continue
            
            dataset_type = self._get_dataset_type(url)
            chunks = self.chunk_text(text)
            
            valid_chunks = []
            for i, chunk in enumerate(chunks):
                self.stats["total_chunks_processed"] += 1
                
                # Level 2 Dedup: Hash
                chunk_hash = self._compute_hash(chunk)
                if self.check_duplicate_hash(chunk_hash):
                    self.stats["duplicates_skipped_hash"] += 1
                    continue
                
                # Embed via Hosted Inference
                embedding = embed_passage(chunk)
                
                # Level 3 Dedup: Similarity
                if self.check_similarity(embedding):
                    self.stats["duplicates_skipped_similarity"] += 1
                    continue
                
                # Prepare for upsert
                chunk_id = f"{dataset_type}_{chunk_hash[:16]}_{i}"
                valid_chunks.append({
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": {
                        "text": chunk,
                        "source": url,
                        "datasetType": dataset_type,
                        "chunkHash": chunk_hash,
                        "ingestedAt": datetime.now().isoformat()
                    }
                })
                
                # Batch upsert every 50 chunks to avoid payload limits
                if len(valid_chunks) >= 50:
                    self.index.upsert(vectors=valid_chunks)
                    self.stats["total_chunks_inserted"] += len(valid_chunks)
                    valid_chunks = []

            # Upsert remaining
            if valid_chunks:
                self.index.upsert(vectors=valid_chunks)
                self.stats["total_chunks_inserted"] += len(valid_chunks)
            
            self._save_url(url)
            self.stats["total_pages_ingested"] += 1
            self.stats["dataset_counts"][dataset_type] = self.stats["dataset_counts"].get(dataset_type, 0) + 1
            
            # Small delay to be polite to servers
            time.sleep(0.1)

        self.print_report()

    def print_report(self):
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_pages_attempted": self.stats["total_pages_attempted"],
                "total_pages_ingested": self.stats["total_pages_ingested"],
                "total_chunks_processed": self.stats["total_chunks_processed"],
                "total_chunks_inserted": self.stats["total_chunks_inserted"]
            },
            "deduplication": {
                "url_skipped": self.stats["duplicates_skipped_url"],
                "hash_skipped": self.stats["duplicates_skipped_hash"],
                "similarity_skipped": self.stats["duplicates_skipped_similarity"]
            },
            "dataset_breakdown": self.stats["dataset_counts"]
        }
        
        print("\n" + "="*50)
        print("INGESTION REPORT")
        print("="*50)
        print(json.dumps(report, indent=4))
        print("="*50 + "\n")
        
        # Save report to file
        report_file = f"ingestion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=4)
        print(f"Report saved to {report_file}")

if __name__ == "__main__":
    # Load URLs from disease_urls.json
    urls_file = "disease_urls.json"
    if not os.path.exists(urls_file):
        print(f"Error: {urls_file} not found.")
    else:
        with open(urls_file, "r") as f:
            data = json.load(f)
            all_urls = data.get("urls", [])
        
        if not all_urls:
            print("No URLs found in disease_urls.json")
        else:
            ingester = MedicalIngester()
            
            # Check if we should run all or just a test
            import sys
            if len(sys.argv) > 1 and sys.argv[1] == "--full":
                urls_to_ingest = all_urls
            else:
                print("Running in TEST mode (first 5 URLs). Use --full for all.")
                urls_to_ingest = all_urls[:5]
                
            ingester.ingest(urls_to_ingest)
