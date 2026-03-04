from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from database import get_db
from perf_pipeline import parallel_pipeline

router = APIRouter(prefix="/query", tags=["QueryOptimized"])

@router.post("/parallel")
async def parallel_query(payload: dict = Body(...), db=Depends(get_db)):
    text = payload.get("text_query", "")
    email = payload.get("email", "")
    data = await parallel_pipeline(text, db, email)
    return JSONResponse(data)

