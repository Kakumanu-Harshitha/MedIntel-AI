import asyncio
import uuid
import sys
import os

# Add the backend directory to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.unified_pipeline import unified_pipeline

async def test_followup_flow():
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    
    print("--- STEP 1: Single Symptom ---")
    res1 = await unified_pipeline.process_request("I have a headache", session_id=session_id)
    print(f"User: I have a headache")
    print(f"AI Advice: {res1.get('advice')}")
    print(f"AI Reason: {res1.get('reason')}")
    print(f"Risk Level: {res1.get('risk_level')}")
    print(f"Possible Conditions: {[c['name'] for c in res1.get('possible_conditions', [])]}")
    
    print("\n--- STEP 2: Adding Duration ---")
    # Using the exact phrase reported by the user: "from 5 days"
    res2 = await unified_pipeline.process_request("from 5 days", session_id=session_id)
    print(f"User: It's been for 3 days")
    print(f"AI Advice: {res2.get('advice')}")
    print(f"AI Reason: {res2.get('reason')}")
    print(f"Risk Level: {res2.get('risk_level')}")
    print(f"Possible Conditions: {[c['name'] for c in res2.get('possible_conditions', [])]}")

    print("\n--- STEP 3: Adding another symptom ---")
    res3 = await unified_pipeline.process_request("I also feel nauseous", session_id=session_id)
    print(f"User: I also feel nauseous")
    print(f"AI Advice: {res3.get('advice')}")
    print(f"AI Reason: {res3.get('reason')}")
    print(f"Risk Level: {res3.get('risk_level')}")
    print(f"Possible Conditions: {[c['name'] for c in res3.get('possible_conditions', [])]}")

if __name__ == "__main__":
    asyncio.run(test_followup_flow())
