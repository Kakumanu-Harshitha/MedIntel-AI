import os
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# --- Initialize MongoDB Client ---
MONGO_URI = os.getenv("MONGO_URI")
memory_collection = None
feedback_collection = None
analytics_collection = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI)
        db = client["Health_Assistant"]
        memory_collection = db["Health_Memory"]
        feedback_collection = db["Health_Feedback"]
        analytics_collection = db["Health_Analytics"]
        print("✅ MongoDB client initialized.")
    except Exception as e:
        print(f"⚠️ WARNING: Could not connect to MongoDB. Memory service disabled. Error: {e}")
else:
    print("⚠️ WARNING: MONGO_URI not found! Memory service disabled.")


def store_message(user_id: str, role: str, content: str, audio_url: str = None) -> str:
    """Stores a message in the user's conversation history. Returns the string ID."""
    if memory_collection is None: return None
    try:
        result = memory_collection.insert_one({
            "user_id": user_id,
            "role": role,
            "content": content,
            "audio_url": audio_url,
            "timestamp": datetime.now(timezone.utc)
        })
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ ERROR: Failed to store message in MongoDB. Error: {e}")
        return None

def log_feedback(user_id: str, rating: str, comment: str = None, context: str = None):
    """Logs user feedback (helpful/not helpful)."""
    if feedback_collection is None: return
    try:
        feedback_collection.insert_one({
            "user_id": user_id,
            "rating": rating, # "positive" or "negative"
            "comment": comment,
            "context": context,
            "timestamp": datetime.now(timezone.utc)
        })
    except Exception as e:
        print(f"❌ ERROR: Failed to log feedback. Error: {e}")

def log_analytics(event_type: str, details: dict):
    """Logs system events for analysis (e.g., Escalation triggered)."""
    if analytics_collection is None: return
    try:
        analytics_collection.insert_one({
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc)
        })
    except Exception as e:
        print(f"❌ ERROR: Failed to log analytics. Error: {e}")

def get_user_memory(user_id: str, limit: int = 10) -> list:
    """Retrieves the last 'limit' messages for the LLM, in chronological order (Oldest -> Newest)."""
    if memory_collection is None: return []
    try:
        # Retrieve the most recent messages first to apply the limit correctly
        messages = list(memory_collection.find(
            {"user_id": user_id},
            {"_id": 0, "role": 1, "content": 1, "audio_url": 1} 
        ).sort("timestamp", -1).limit(limit))
        
        # Reverse the results so they are in chronological order (Oldest -> Newest)
        return list(reversed(messages))
    except Exception as e:
        print(f"❌ ERROR: Failed to retrieve user memory from MongoDB. Error: {e}")
        return []

def get_full_history_for_dashboard(user_id: str, limit: int = 100) -> list:
    """Retrieves full history with timestamps for the dashboard view, in chronological order (Oldest -> Newest)."""
    if memory_collection is None: return []
    try:
        # Step 1: Get the latest N messages (descending order)
        messages = list(memory_collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit))
        
        # Step 2: Convert ObjectId to string for JSON serialization
        for msg in messages:
            msg["query_id"] = str(msg["_id"])
            del msg["_id"]
        
        # Step 3: Reverse them to restore chronological order (Oldest -> Newest)
        # This ensures the oldest message is at the top [0] and newest at the bottom [last]
        return list(reversed(messages))
    except Exception as e:
        print(f"❌ ERROR: Failed to retrieve dashboard history from MongoDB. Error: {e}")
        return []

def clear_user_memory(user_id: str):
    """Clears all conversation history for a user."""
    if memory_collection is None: return
    try:
        memory_collection.delete_many({"user_id": user_id})
        print(f"✅ Memory cleared for user: {user_id}")
    except Exception as e:
        print(f"❌ ERROR: Failed to clear user memory. Error: {e}")
