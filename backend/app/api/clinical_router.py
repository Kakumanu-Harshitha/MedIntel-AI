from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
from fastapi.responses import JSONResponse

from app.services.unified_pipeline import unified_pipeline

router = APIRouter(prefix="/clinical", tags=["Clinical Memory Engine"])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

@router.post("/chat")
async def clinical_chat(payload: ChatRequest):
    """
    Process a clinical chat request using the Unified Pipeline.
    Returns a structured JSON response.
    """
    try:
        response_data = await unified_pipeline.process_request(
            message=payload.message,
            session_id=payload.session_id
        )
        return JSONResponse(content=response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat_stream")
async def clinical_chat_stream(payload: ChatRequest):
    """
    Stream the response (Simulated for compatibility).
    """
    # For now, we just wait for the full response and stream it as one event
    # because the new architecture prioritizes safety and validation over token streaming.
    try:
        response_data = await unified_pipeline.process_request(
            message=payload.message,
            session_id=payload.session_id
        )
        
        async def event_generator():
            yield f"data: {json.dumps(response_data)}\n\n"
            
        from fastapi.responses import StreamingResponse
        return StreamingResponse(event_generator(), media_type="text/event-stream")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
