import asyncio
from playwright.async_api import async_playwright
import time
import json

GRAPHQL_URL = "https://pcmap-api.place.naver.com/graphql"


QUERY = """
query getRestaurants {
  restaurants: restaurantList(input: {query: "서울"}) {
    items {
      id
      name
      x
      y
      __typename
    }
    total
    __typename
  }
}
"""

BODY = {
    "operationName": "getRestaurants",
    "variables": {},
    "query": QUERY
}

async def make_single_request(session_id):
    """Single GraphQL request using Playwright - retry until success"""
    retry_count = 0
    
    while True:
        retry_count += 1
        print(f"Request {session_id}: Attempt {retry_count}...")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Access Naver Map first to set cookies
                await page.goto('https://map.naver.com/', timeout=10000)
                await asyncio.sleep(1)  # Wait for page loading
                
                # Execute GraphQL request
                response = await page.request.post(
                    GRAPHQL_URL,
                    data=json.dumps(BODY),
                    headers={
                        'accept': '*/*',
                        'accept-language': 'ko-KR,ko;q=0.9,en;q=0.8',
                        'content-type': 'application/json',
                        'referer': 'https://map.naver.com/',
                        'origin': 'https://map.naver.com'
                    },
                    timeout=15000
                )
                
                # Read response first, then close browser
                if response.status == 200:
                    # response_text = await response.text()
                    print(f"Request {session_id}: ✅ Success (200) - Attempt {retry_count}")
                    # print(f"Response data: {response_text}")
                    await browser.close()
                    return True
                else:
                    print(f"Request {session_id}: ❌ Failed ({response.status}) - Retrying...")
                    await browser.close()
                    # No sleep - retry immediately
                    
        except Exception as e:
            print(f"Request {session_id}: 💥 Exception ({str(e)}) - Retrying...")
            # No sleep - retry immediately

async def test_playwright_parallel_requests(num_requests=10, start_id=1):
    """Execute requests in parallel"""
    print(f"Executing {num_requests} parallel requests...")
    
    start_time = time.time()
    
    # Execute all requests in parallel with proper IDs
    tasks = [make_single_request(start_id + i) for i in range(num_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Count results
    success_count = sum(1 for result in results if result is True)
    failure_count = num_requests - success_count
    
    print(f"Completed in {execution_time:.2f} seconds")
    print(f"Results: Success: {success_count} | Failed: {failure_count}")
    print(f"Success rate: {(success_count/num_requests)*100:.1f}%")
    
    return success_count, failure_count, execution_time

if __name__ == "__main__":
    # Test with single request first
    async def test_single():
        print("Testing single request...")
        result = await make_single_request(1)
        print(f"Single request result: {result}")
    
    # Test with parallel requests
    async def main():
        NUM_REQUESTS = 3  # Reduce to 3 for Ubuntu testing
        request_counter = 0
        
        while True:
            request_counter += 1
            batch_start = (request_counter - 1) * NUM_REQUESTS + 1
            batch_end = request_counter * NUM_REQUESTS
            
            print(f"\n=== Batch {request_counter} (Requests {batch_start}-{batch_end}) ===")
            success_count, failure_count, execution_time = await test_playwright_parallel_requests(num_requests=NUM_REQUESTS, start_id=batch_start)
            
            # Calculate remaining wait time
            remaining_wait = max(0, NUM_REQUESTS - execution_time)
            print(f"Waiting {remaining_wait:.1f} seconds before next batch...")
            await asyncio.sleep(remaining_wait+1)
    
    # Uncomment one of these to test:
    # asyncio.run(test_single())  # Test single request first
    asyncio.run(main())  # Test parallel requests
