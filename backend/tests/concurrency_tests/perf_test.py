import asyncio
import httpx
import time
import statistics
import sys
import argparse

async def send_query(client, url, query_text, email):
    start_time = time.perf_counter()
    try:
        response = await client.post(
            url,
            json={"text_query": query_text, "email": email},
            timeout=30.0
        )
        end_time = time.perf_counter()
        
        status = response.status_code
        duration = end_time - start_time
        
        if status == 200:
            return True, duration
        else:
            print(f"DEBUG: Status {status} for {query_text[:20]}...")
            return False, duration
    except Exception as e:
        end_time = time.perf_counter()
        print(f"DEBUG: Exception {type(e).__name__}: {str(e)}")
        return False, end_time - start_time

async def run_load_test(concurrency):
    url = "http://127.0.0.1:8000/query/parallel"
    query_text = "I have a headache and I might need a lab report"
    email = "test@example.com"
    
    print(f"\n--- Starting Load Test: {concurrency} Concurrent Users ---")
    
    async with httpx.AsyncClient() as client:
        start_batch = time.perf_counter()
        tasks = [send_query(client, url, query_text, email) for _ in range(concurrency)]
        results = await asyncio.gather(*tasks)
        end_batch = time.perf_counter()
        
    durations = [d for success, d in results if success]
    failures = concurrency - len(durations)
    
    total_time = end_batch - start_batch
    
    print(f"Total Batch Time: {total_time:.4f}s")
    if durations:
        print(f"Average Latency: {statistics.mean(durations):.4f}s")
        print(f"Min Latency:     {min(durations):.4f}s")
        print(f"Max Latency:     {max(durations):.4f}s")
    print(f"Successful:      {len(durations)}")
    print(f"Failed:          {failures}")
    print(f"Error Rate:      {(failures/concurrency)*100:.1f}%")
    print(f"Throughput:      {(concurrency/total_time):.2f} req/s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    
    asyncio.run(run_load_test(args.concurrency))
