import os
import json
import uuid
import re
from datetime import datetime, timezone
from typing import Optional
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# --- Initialize MongoDB Client ---
MONGO_URI = os.getenv("MONGO_URI")
if MONGO_URI:
    # Remove any quotes if present in .env
    MONGO_URI = MONGO_URI.strip("'").strip('"')
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


def _clean_content(content: str) -> str:
    """Helper to convert JSON responses into human-readable text for LLM context."""
    if not content: return ""
    
    # Try to parse as JSON
    try:
        data = json.loads(content)
        if not isinstance(data, dict): return content
        
        # Extract meaningful fields based on known types
        if data.get("status") == "HITL_ESCALATED":
            return data.get("message", "Request flagged for human review.")
        
        if data.get("type") == "chat_message":
            return data.get("message", content)

        if data.get("type") == "health_report":
            return data.get("health_information", content)
            
        if data.get("type") == "medical_report_analysis":
            return data.get("summary", content)
            
        if data.get("input_type") == "medical_image":
            obs = data.get("observations", [])
            obs_str = ", ".join(obs) if isinstance(obs, list) else str(obs)
            return f"Image Analysis: {obs_str}. {data.get('general_advice', '')}"
            
        if data.get("input_type") == "medical_report":
            return data.get("interpretation", content)
            
        if data.get("type") == "clarification_questions":
            questions = data.get("questions", [])
            q_str = " ".join(questions) if isinstance(questions, list) else str(questions)
            return f"Question: {data.get('context', '')} {q_str}"
            
        # Fallback for other JSON types
        return data.get("summary", data.get("message", content))
        
    except (json.JSONDecodeError, TypeError):
        # Not JSON or not a dict, return as is
        return content

def store_message(user_id: str, role: str, content: str, report_type: str = None, pdf_url: str = None, force_report: bool = False):
    """Stores a message in the user's conversation history."""
    if memory_collection is None: return None
    try:
        doc = {
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }
        
        report_id = None
        # If it's an assistant message, check if it contains a report and assign a report_id
        if role == "assistant":
            is_report = False
            parsed = None
            
            # Try to parse as JSON
            try:
                # Use regex to find JSON if there's surrounding text
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(1))
                else:
                    parsed = json.loads(content)
            except:
                parsed = None

            if parsed:
                # 1. Define Strict Report Eligibility
                # Save into Report History ONLY if the assistant response JSON has:
                # "type": "health_report" OR "type": "medical_report_analysis"
                # OR if it's an image analysis (medical_image)
                report_type_field = parsed.get("type") or parsed.get("input_type")
                
                if report_type_field in ["health_report", "medical_report_analysis", "medical_image"]:
                    is_report = True
                # 2. Check for force_report flag (e.g. from file upload)
                elif force_report:
                    is_report = True
                else:
                    is_report = False
            
            if is_report:
                report_id = str(uuid.uuid4())
                doc["report_id"] = report_id
                # Store additional report metadata for easier retrieval
                doc["report_type"] = report_type or (parsed.get("type") if parsed else None) or "general"
                doc["pdf_url"] = pdf_url

        memory_collection.insert_one(doc)
        return report_id
    except Exception as e:
        print(f"❌ ERROR: Failed to store message in MongoDB. Error: {e}")
        return None

def get_report_by_id(user_id: str, report_id: str) -> dict:
    """Retrieves a specific report message from history by report_id."""
    if memory_collection is None: return None
    try:
        msg = memory_collection.find_one({
            "user_id": user_id,
            "report_id": report_id
        })
        if msg and msg.get("content"):
            try:
                return json.loads(msg["content"])
            except:
                return None
        return None
    except Exception as e:
        print(f"❌ ERROR: Failed to retrieve report by ID. Error: {e}")
        return None

def log_feedback(user_id: str, rating: str, comment: str = None, context: str = None, report_id: str = None):
    """Logs user feedback (helpful/not helpful)."""
    if feedback_collection is None: return
    try:
        feedback_collection.insert_one({
            "user_id": user_id,
            "rating": rating, # "positive" or "negative"
            "comment": comment,
            "context": context,
            "report_id": report_id,
            "timestamp": datetime.utcnow()
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
            "timestamp": datetime.utcnow()
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
            {"_id": 0, "role": 1, "content": 1} 
        ).sort("timestamp", -1).limit(limit))
        
        # Clean the content for LLM consumption
        for msg in messages:
            if msg.get("role") == "assistant":
                msg["content"] = _clean_content(msg.get("content", ""))
        
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
            {"user_id": user_id},
            {"_id": 0} 
        ).sort("timestamp", -1).limit(limit))
        
        # Step 2: Check feedback status for assistant reports
        for msg in messages:
            report_id = msg.get("report_id")
            if report_id and feedback_collection is not None:
                feedback = feedback_collection.find_one({"report_id": report_id, "user_id": user_id})
                if feedback:
                    msg["feedback_rating"] = feedback.get("rating")

        # Step 3: Reverse them to restore chronological order (Oldest -> Newest)
        # This ensures the oldest message is at the top [0] and newest at the bottom [last]
        return list(reversed(messages))
    except Exception as e:
        print(f"❌ ERROR: Failed to retrieve dashboard history from MongoDB. Error: {e}")
        return []

def get_reports_history(user_id: str, limit: int = 50) -> list:
    """Retrieves only messages that are valid reports for the Reports page."""
    if memory_collection is None: return []
    try:
        # We search for documents that have a report_id (which are gated during store_message)
        messages = list(memory_collection.find(
            {
                "user_id": user_id,
                "report_id": {"$exists": True, "$ne": None}
            },
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit))
        
        # Check feedback status for each report
        for msg in messages:
            report_id = msg.get("report_id")
            if report_id and feedback_collection is not None:
                feedback = feedback_collection.find_one({"report_id": report_id, "user_id": user_id})
                if feedback:
                    msg["feedback_rating"] = feedback.get("rating")
        
        return list(reversed(messages))
    except Exception as e:
        print(f"❌ ERROR: Failed to retrieve reports history. Error: {e}")
        return []

def clear_user_memory(user_id: str):
    """Clears all conversation history for a user."""
    if memory_collection is None: return
    try:
        memory_collection.delete_many({"user_id": user_id})
        print(f"✅ Memory cleared for user: {user_id}")
    except Exception as e:
        print(f"❌ ERROR: Failed to clear user memory. Error: {e}")

def get_feedback_metrics():
    """Retrieves satisfaction metrics for the owner dashboard."""
    if feedback_collection is None:
        return {
            "helpfulness_rate": 0,
            "total_feedback": 0,
            "reasons_breakdown": {},
            "recent_feedback": []
        }
    try:
        total_feedback = feedback_collection.count_documents({})
        helpful_count = feedback_collection.count_documents({"rating": "positive"})
        helpfulness_rate = (helpful_count / total_feedback * 100) if total_feedback > 0 else 0
        
        # Negative feedback breakdown by reason
        # We'll parse the 'comment' field which contains "Reason: Optional Text"
        pipeline = [
            {"$match": {"rating": "negative"}},
            {"$group": {
                "_id": {"$arrayElemAt": [{"$split": ["$comment", ": "]}, 0]},
                "count": {"$sum": 1}
            }}
        ]
        reasons = list(feedback_collection.aggregate(pipeline))
        reasons_breakdown = {r["_id"]: r["count"] for r in reasons if r["_id"]}

        # Recent feedback list
        recent_feedback = list(feedback_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(50))
        for f in recent_feedback:
            if f.get("timestamp"):
                f["timestamp"] = f["timestamp"].isoformat()

        return {
            "helpfulness_rate": round(helpfulness_rate, 2),
            "total_feedback": total_feedback,
            "reasons_breakdown": reasons_breakdown,
            "recent_feedback": recent_feedback
        }
    except Exception as e:
        print(f"❌ ERROR: Failed to get feedback metrics. Error: {e}")
        return {
            "helpfulness_rate": 0,
            "total_feedback": 0,
            "reasons_breakdown": {},
            "recent_feedback": []
        }

