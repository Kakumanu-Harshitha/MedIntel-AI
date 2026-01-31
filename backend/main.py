# backend/main.py
import os
import sys

# Add the current directory to sys.path to ensure local imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from auth import router as auth_router
from profile_router import router as profile_router
from report_router import router as report_router
from security_router import router as security_router
from feedback_router import router as feedback_router
from owner_router import router as owner_router
import query_service, dashboard_service  
import models  
import os
import time
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from audit_logger import audit_logger
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="AI Health Assistant API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create tables
# Base.metadata.create_all(bind=engine)

# Mount static directory for audio
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit Logging Middleware
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log critical or suspicious activities (e.g., 4xx, 5xx errors)
    if response.status_code >= 400:
        # Avoid logging common 404s or 401s if they are already handled in routers
        # but capture 500s and other critical errors
        if response.status_code >= 500:
             await audit_logger.log_event(
                action="SYSTEM_ERROR",
                status="FAILURE",
                request=request,
                metadata={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2)
                }
            )
            
    return response

# Include routers
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(report_router)
app.include_router(security_router)
app.include_router(feedback_router)
app.include_router(owner_router)
app.include_router(query_service.router)
app.include_router(dashboard_service.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Health Assistant API"}
