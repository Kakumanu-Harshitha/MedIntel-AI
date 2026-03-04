import os
import asyncio
import json
from typing import Any, Dict, List, Tuple
from app.database.cache import AsyncCache, CacheKeys

from sentence_transformers import SentenceTransformer
from pinecone import Pinecone

_EMB_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")
_PINECONE_INDEX = os.getenv("PINECONE_INDEX", "medical-memory")

_emb = SentenceTransformer(_EMB_MODEL_NAME)
_pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
_index = _pc.Index(_PINECONE_INDEX)

_cache = AsyncCache()
_keys = CacheKeys(emb_model=_EMB_MODEL_NAME, index_name=_PINECONE_INDEX, rsp_version=os.getenv("RSP_VERSION", "v1"))


def _norm_text(t: str) -> str:
    return " ".join(t.split()).strip().lower()


def _simple_rules(text: str) -> str:
    t = _norm_text(text)
    if "lab" in t or "cbc" in t:
        return "LabReport"
    if "image" in t or "x-ray" in t or "scan" in t:
        return "Image"
    return "General"


async def detect_intent(text: str) -> str:
    return await asyncio.to_thread(_simple_rules, text)


async def embed_text(text: str) -> List[float]:
    key = _keys.emb_key(text)
    hit = await _cache.get(key)
    if hit:
        return json.loads(hit.decode())
    vec = await asyncio.to_thread(_emb.encode, text)
    await _cache.set(key, json.dumps(vec).encode(), ttl=60 * 60 * 24 * 7)
    return vec


async def vector_search(vec: List[float], top_k: int = 8) -> List[Dict[str, Any]]:
    packed = json.dumps([round(x, 6) for x in vec]).encode()
    key = _keys.ret_key(packed, top_k)
    hit = await _cache.get(key)
    if hit:
        return json.loads(hit.decode())
    res = await asyncio.to_thread(_index.query, vector=vec, top_k=top_k, include_metadata=True)
    matches = res.get("matches", [])
    await _cache.set(key, json.dumps(matches).encode(), ttl=60 * 10)
    return matches


def _get_profile_sync(db, email: str) -> Dict[str, Any]:
    from app.models.models import Profile
    row = db.query(Profile).filter(Profile.email == email).first()
    if not row:
        return {}
    return {
        "email": row.email,
        "age": row.age,
        "gender": row.gender
    }


async def fetch_profile(db, email: str) -> Dict[str, Any]:
    return await asyncio.to_thread(_get_profile_sync, db, email)


async def parallel_pipeline(text: str, db, email: str) -> Dict[str, Any]:
    t1 = asyncio.create_task(detect_intent(text))
    t2 = asyncio.create_task(embed_text(text))
    intent, vec = await asyncio.gather(t1, t2)
    t3 = asyncio.create_task(vector_search(vec))
    t4 = asyncio.create_task(fetch_profile(db, email))
    matches, profile = await asyncio.gather(t3, t4)
    return {
        "intent": intent,
        "matches": matches,
        "profile": profile
    }

