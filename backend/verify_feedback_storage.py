
import os
import json
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("❌ MONGO_URI not found!")
    exit(1)

client = MongoClient(MONGO_URI)
db = client["Health_Assistant"]
feedback_collection = db["Health_Feedback"]
memory_collection = db["Health_Memory"]

def verify_storage():
    print("--- Verifying Feedback Storage ---")
    count = feedback_collection.count_documents({})
    print(f"Total feedback records: {count}")
    
    if count > 0:
        latest = feedback_collection.find_one(sort=[("timestamp", -1)])
        print("\nLatest Feedback:")
        print(f"  User ID: {latest.get('user_id')}")
        print(f"  Rating: {latest.get('rating')}")
        print(f"  Report ID: {latest.get('report_id')}")
        print(f"  Timestamp: {latest.get('timestamp')}")
        
        # Check if the corresponding report exists in memory
        if latest.get('report_id'):
            report = memory_collection.find_one({"report_id": latest.get('report_id')})
            if report:
                print(f"✅ Found corresponding report in memory.")
            else:
                print(f"❌ Corresponding report NOT found in memory for report_id: {latest.get('report_id')}")
    else:
        print("No feedback found in collection.")

if __name__ == "__main__":
    verify_storage()
