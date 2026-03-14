# backend/structured_memory.py
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

# --- Initialize MongoDB Client ---
MONGO_URI = os.getenv("MONGO_URI")
memory_collection = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI)
        db = client["Health_Assistant"]
        memory_collection = db["Structured_Health_Memory"]
        print("[OK] Structured Memory MongoDB client initialized.")
    except Exception as e:
        print(f"[WARNING] Could not connect to MongoDB for structured memory. Error: {e}")
else:
    print("[WARNING] MONGO_URI not found for structured memory.")

class StructuredMemory:
    def store_chunk(self, user_id: str, chunk_type: str, content: str, confidence: str = "user_reported"):
        """
        Stores a specific medical context chunk (e.g., past_symptom, allergy, preference, medication).
        """
        if memory_collection is None: return
        try:
            # If it's a medication, we might want to ensure we don't store duplicates
            if chunk_type == "medication":
                # Basic check to see if this medication is already listed
                existing = memory_collection.find_one({"user_id": user_id, "type": "medication", "content": content})
                if existing:
                    print(f"[INFO] Medication '{content}' already in memory for user {user_id}")
                    return

            memory_collection.insert_one({
                "user_id": user_id,
                "type": chunk_type,
                "content": content,
                "confidence": confidence,
                "timestamp": datetime.utcnow()
            })
            print(f"[OK] Stored {chunk_type} for user {user_id}")
        except Exception as e:
            print(f"[ERROR] Failed to store structured memory chunk. Error: {e}")

    def get_relevant_history(self, user_id: str, query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves medically relevant chunks for the current query.
        Currently simple retrieval, but can be expanded to semantic search.
        """
        if memory_collection is None: return []
        try:
            # For now, get the most recent relevant chunks
            chunks = memory_collection.find(
                {"user_id": user_id},
                {"_id": 0, "type": 1, "content": 1, "timestamp": 1}
            ).sort("timestamp", -1).limit(limit)
            return list(chunks)
        except Exception as e:
            print(f"[ERROR] Failed to retrieve structured memory. Error: {e}")
            return []

    def summarize_memory(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Converts memory chunks into a readable string for LLM context.
        """
        if not chunks:
            return "No relevant past medical context found."
        
        summary = "Known medical context from previous interactions:\n"
        for chunk in chunks:
            summary += f"- [{chunk['type']}] {chunk['content']}\n"
        return summary

# Instantiate the service
structured_memory = StructuredMemory()

