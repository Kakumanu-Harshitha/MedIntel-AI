
import sys
import os
import json
from datetime import datetime, timezone
import uuid

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import mongo_memory

def test_storage_gating():
    print("\n" + "="*20 + " Storage Gating Verification " + "="*20)
    
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    # 1. Test Casual Chat (Should NOT have report_id)
    print("\n[Test 1] Storing Casual Chat...")
    casual_chat = json.dumps({
        "type": "chat_message",
        "message": "Hi! 👋 How can I help you today?"
    })
    rid1 = mongo_memory.store_message(test_user_id, "assistant", casual_chat)
    print(f"  Result report_id: {rid1}")
    assert rid1 is None, "❌ FAIL: Casual chat should NOT generate a report_id"
    print("  ✅ PASS: Casual chat ignored.")

    # 2. Test Real Health Report (Should HAVE report_id)
    print("\n[Test 2] Storing Health Report...")
    health_report = json.dumps({
        "type": "health_report",
        "health_information": "Information about headaches.",
        "possible_conditions": ["Tension headache"],
        "reasoning_brief": "User reported head pain.",
        "recommended_next_steps": "Rest and hydrate.",
        "ai_confidence": "High",
        "trusted_sources": ["Medical Knowledge Base"],
        "disclaimer": "Not a diagnosis."
    })
    rid2 = mongo_memory.store_message(test_user_id, "assistant", health_report)
    print(f"  Result report_id: {rid2}")
    assert rid2 is not None, "❌ FAIL: Health report SHOULD generate a report_id"
    print("  ✅ PASS: Health report stored.")

    # 3. Test Medical Report Analysis (Should HAVE report_id)
    print("\n[Test 3] Storing Medical Report Analysis...")
    lab_analysis = json.dumps({
        "type": "medical_report_analysis",
        "summary": "Your blood test looks normal.",
        "test_analysis": [{"test_name": "Glucose", "value": "90", "status": "Normal"}],
        "general_guidance": ["Keep up the good work."],
        "disclaimer": "Not a diagnosis."
    })
    rid3 = mongo_memory.store_message(test_user_id, "assistant", lab_analysis)
    print(f"  Result report_id: {rid3}")
    assert rid3 is not None, "❌ FAIL: Medical report analysis SHOULD generate a report_id"
    print("  ✅ PASS: Medical report analysis stored.")

    # 4. Test Reports History Retrieval (Should only return the 2 reports)
    print("\n[Test 4] Verifying Reports History...")
    history = mongo_memory.get_reports_history(test_user_id)
    print(f"  Items in history: {len(history)}")
    for item in history:
        print(f"    - Found report_id: {item.get('report_id')} | type: {item.get('report_type')}")
    
    assert len(history) == 2, f"❌ FAIL: Expected 2 reports in history, found {len(history)}"
    print("  ✅ PASS: History correctly filtered.")

    # Cleanup
    mongo_memory.clear_user_memory(test_user_id)
    print(f"\n✅ Verification Complete: All tests passed for user {test_user_id}")

if __name__ == "__main__":
    test_storage_gating()
