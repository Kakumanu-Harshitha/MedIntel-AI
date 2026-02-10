import traceback
import os
from datetime import datetime

LOG_FILE = "backend_debug.log"

def log_debug_error(context: str, error: Exception):
    timestamp = datetime.now().isoformat()
    error_msg = f"\n{'='*50}\n[{timestamp}] ERROR in {context}:\n{str(error)}\n{traceback.format_exc()}\n{'='*50}\n"
    
    with open(LOG_FILE, "a") as f:
        f.write(error_msg)
    print(error_msg)
