import os
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse
from groq import AsyncGroq

router = APIRouter(prefix="/stream", tags=["Streaming"])
_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None

@router.post("/chat")
async def stream_chat(body: dict = Body(...)):
    prompt = body.get("prompt", "")
    async def gen() -> AsyncGenerator[bytes, None]:
        if not _client:
            yield b""
            return
        stream = await _client.chat.completions.create(
            model=os.getenv("PRIMARY_LLM_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            temperature=0.2
        )
        async for chunk in stream:
            c = None
            try:
                c = chunk.choices[0].delta.content
            except Exception:
                c = None
            if c:
                yield c.encode("utf-8")
            await asyncio.sleep(0)
    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")

