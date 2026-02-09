
import sys
import os
import asyncio
import json
from typing import Dict, Any, List

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_router import RAGRouter, QueryIntent

async def test_small_talk_detection():
    print("\n" + "="*20 + " Small Talk Detection Test " + "="*20)
    router = RAGRouter()
    
    cases = [
        # Small Talk cases
        ("hi", QueryIntent.SMALL_TALK),
        ("hello", QueryIntent.SMALL_TALK),
        ("hey", QueryIntent.SMALL_TALK),
        ("good morning", QueryIntent.SMALL_TALK),
        ("thanks", QueryIntent.SMALL_TALK),
        ("thank you", QueryIntent.SMALL_TALK),
        ("bye", QueryIntent.SMALL_TALK),
        ("see you", QueryIntent.SMALL_TALK),
        ("ok", QueryIntent.SMALL_TALK),
        ("nice", QueryIntent.SMALL_TALK),
        ("hi there", QueryIntent.SMALL_TALK),
        
        # Mixed cases (Should NOT be SMALL_TALK)
        ("hi, i have a headache", QueryIntent.SYMPTOM_QUERY),
        ("hello, tell me about diabetes", QueryIntent.DISEASE_QUERY),
        ("thanks, but what is malaria?", QueryIntent.DISEASE_QUERY),
        
        # Other intents
        ("what is dengue?", QueryIntent.DISEASE_QUERY),
        ("i have chest pain", QueryIntent.EMERGENCY_QUERY),
    ]
    
    for query, expected in cases:
        detected = router.detect_intent(query)
        print(f"Query: '{query}'")
        print(f"  Detected: {detected.name} | {'PASS' if detected == expected else 'FAIL (Expected ' + expected.name + ')'}")

if __name__ == "__main__":
    asyncio.run(test_small_talk_detection())
