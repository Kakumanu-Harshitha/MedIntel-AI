from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

# Import Routers
from app.auth.logic.auth import router as auth_router
from app.api.clinical_router import router as clinical_router
from app.api.feedback_router import router as feedback_router
from app.admin.dashboard_service import router as dashboard_router
from app.api.profile_router import router as profile_router
from app.api.owner_router import router as owner_router
from app.api.parallel_router import router as parallel_router
from app.api.security_router import router as security_router
from app.api.report_router import router as report_router
from app.api.streaming_router import router as streaming_router
from app.api.query_service import router as query_router

# Initialize App
app = FastAPI(
    title="AI Health Assistant API",
    description="Backend for AI Health Assistant with Unified Pipeline",
    version="2.0.0"
)

# CORS Configuration
origins = [
    "http://localhost:5173", # Frontend dev server
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "*" # Allow all for dev
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files - use absolute path so it works from any CWD
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(os.path.join(_static_dir, "audio"), exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# Include Routers
app.include_router(auth_router)
app.include_router(clinical_router)
app.include_router(feedback_router)
app.include_router(dashboard_router)
app.include_router(profile_router)
app.include_router(owner_router)
app.include_router(parallel_router)
app.include_router(security_router)
app.include_router(report_router)
app.include_router(streaming_router)
app.include_router(query_router)

@app.get("/")
async def root():
    return {"message": "AI Health Assistant API is running"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
