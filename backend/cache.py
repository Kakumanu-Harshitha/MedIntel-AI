import hashlib
import json
import os
from typing import Optional
import redis.asyncio as redis

class AsyncCache:
    def __init__(self, redis_url: str = None):
        if not redis_url:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url)

    def get_cache_key(self, state, route) -> str:
        key = {
            "symptoms": sorted(state.symptoms),
            "duration": state.duration,
            "route": route.value
        }
        return hashlib.md5(json.dumps(key).encode()).hexdigest()

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ttl: int = 3600):
        await self.redis.set(key, value, ex=ttl)

class CacheKeys:
    def __init__(self, emb_model: str, index_name: str, rsp_version: str):
        self.emb_model = emb_model
        self.index_name = index_name
        self.rsp_version = rsp_version

    def emb_key(self, text: str) -> str:
        return hashlib.md5(f"{self.emb_model}:{text}".encode()).hexdigest()

    def ret_key(self, packed: bytes, top_k: int) -> str:
        return hashlib.md5(f"{self.index_name}:{packed}:{top_k}".encode()).hexdigest()
