import asyncio
import time
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock_perf_pipeline import parallel_pipeline

async def run_verification():
    print("--- Verifying Parallel Logic ---")
    start_time = time.perf_counter()
    
    # Run the pipeline
    result = await parallel_pipeline("test query", "test@example.com")
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    print(f"Pipeline Result: {result['intent']}")
    print(f"Total Execution Time: {duration:.4f}s")
    
    # Logic:
    # Phase 1: sleep(0.5) and sleep(1.0) in parallel -> 1.0s
    # Phase 2: sleep(1.5) and sleep(0.5) in parallel -> 1.5s
    # Expected: ~2.5s
    # Sequential: 0.5 + 1.0 + 1.5 + 0.5 = 3.5s
    
    if duration < 3.0:
        print("\nSUCCESS: Parallel processing is WORKING.")
        print(f"Time saved vs sequential: ~{3.5 - duration:.2f}s")
    else:
        print("\nFAILURE: Processing appears to be sequential.")

if __name__ == "__main__":
    asyncio.run(run_verification())
