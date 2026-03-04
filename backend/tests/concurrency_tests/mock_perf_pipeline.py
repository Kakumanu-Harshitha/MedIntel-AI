import asyncio
from typing import Any, Dict, List

async def detect_intent(text: str) -> str:
    await asyncio.sleep(0.5)  # Simulate intent detection
    return "General"

async def embed_text(text: str) -> List[float]:
    await asyncio.sleep(1.0)  # Simulate embedding
    return [0.1] * 768

async def vector_search(vec: List[float], top_k: int = 8) -> List[Dict[str, Any]]:
    await asyncio.sleep(1.5)  # Simulate search
    return [{"id": "mock_id", "score": 0.9}]

async def fetch_profile(db, email: str) -> Dict[str, Any]:
    await asyncio.sleep(0.5)  # Simulate DB fetch
    return {"email": email, "age": 30}

async def parallel_pipeline(text: str, email: str) -> Dict[str, Any]:
    # Phase 1: Intent and Embedding in parallel
    t1 = asyncio.create_task(detect_intent(text))
    t2 = asyncio.create_task(embed_text(text))
    intent, vec = await asyncio.gather(t1, t2)
    
    # Phase 2: Vector Search and Profile Fetch in parallel
    t3 = asyncio.create_task(vector_search(vec))
    t4 = asyncio.create_task(fetch_profile(None, email)) # db is mock none
    matches, profile = await asyncio.gather(t3, t4)
    
    return {
        "intent": intent,
        "matches": matches,
        "profile": profile
    }
