import sys
import os
import asyncio
import json
from typing import Dict, Any, List

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_router import RAGRouter, QueryIntent
from llm_service import run_clinical_analysis, guardrails

async def test_category_a():
    print("\n" + "="*20 + " A) Routing + Intent Detection " + "="*20)
    router = RAGRouter()
    cases = [
        ("What is dengue fever?", QueryIntent.DISEASE_QUERY),
        ("Symptoms of typhoid fever", QueryIntent.DISEASE_QUERY),
        ("How does malaria spread?", QueryIntent.DISEASE_QUERY),
        ("I have headache since morning", QueryIntent.SYMPTOM_QUERY),
        ("My HbA1c is 7.8 and fasting glucose is 160", QueryIntent.TEST_OR_REPORT_QUERY),
        ("Is it safe to take aspirin with warfarin?", QueryIntent.DRUG_INTERACTION_QUERY),
        ("Latest PubMed research on Alzheimer treatment", QueryIntent.RESEARCH_QUERY)
    ]
    for query, expected in cases:
        detected = router.detect_intent(query)
        shortcut = router.should_use_symptom_shortcut(query, detected)
        print(f"Query: '{query}'")
        print(f"  Detected: {detected.name} | Shortcut Allowed: {shortcut} | {'PASS' if detected == expected else 'FAIL'}")

async def test_category_b():
    print("\n" + "="*20 + " B) Emergency Detection " + "="*20)
    cases = [
        "I have chest pain and difficulty breathing",
        "My face is drooping and my speech is slurred",
        "I feel like killing myself"
    ]
    for query in cases:
        result = guardrails.check_safety(query)
        print(f"Query: '{query}'")
        print(f"  Safe: {result['is_safe']}")
        if not result['is_safe']:
            print(f"  Response: {result['response']['summary']} - {result['response']['recommendations']['immediate_action']}")

async def test_category_c_d():
    print("\n" + "="*20 + " C & D) Multimodal & Voice Simulation " + "="*20)
    # Simulating the inputs as they would arrive at the service layer
    cases = [
        {"name": "Skin Rash Image", "inputs": {"image_caption": "Photo of a red bumpy rash on arm (dermatology 0.9)"}},
        {"name": "Prescription OCR", "inputs": {"report_text": "Prescription: Amoxicillin 500mg, 3 times a day for 7 days"}},
        {"name": "Voice Input", "inputs": {"transcribed_text": "I have fever and headache for 2 days"}}
    ]
    router = RAGRouter()
    for case in cases:
        query = f"{case['inputs'].get('text_query', '')} {case['inputs'].get('transcribed_text', '')} {case['inputs'].get('image_caption', '')} {case['inputs'].get('report_text', '')}".strip()
        intent = router.detect_intent(query)
        print(f"Scenario: {case['name']} | Combined Query: '{query[:50]}...'")
        print(f"  Detected Intent: {intent.name}")

async def test_category_e():
    print("\n" + "="*20 + " E) Memory / Health Profile " + "="*20)
    profile = {
        "user_id": "123",
        "age": 20,
        "allergies": "Penicillin",
        "conditions": "Asthma",
        "medications": "Inhaler"
    }
    # Since we can't call the actual LLM easily without keys, we'll check how the profile is handled
    # in the clinical analysis flow.
    print(f"Profile: {profile}")
    print("Testing Query: 'Can I take amoxicillin?'")
    # In a real run, run_clinical_analysis would see 'Penicillin' in profile and 'amoxicillin' in query.
    print("  Expected: System should flag Amoxicillin as a penicillin-class drug.")

async def test_category_g():
    print("\n" + "="*20 + " G) Edge Case Stability " + "="*20)
    router = RAGRouter()
    cases = [
        "vomtings and stomac pain", # Spelling
        "fever",                    # Short
        "hi",                       # Irrelevant
        "tell me a joke"            # Irrelevant
    ]
    for query in cases:
        intent = router.detect_intent(query)
        print(f"Query: '{query}' -> Intent: {intent.name}")

async def main():
    await test_category_a()
    await test_category_b()
    await test_category_c_d()
    await test_category_e()
    await test_category_g()

if __name__ == "__main__":
    asyncio.run(main())
