import requests
import urllib3
import asyncio
import subprocess
import os
from playwright.async_api import async_playwright
from fake_useragent import UserAgent
import time

# HTTPS 인증 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GRAPHQL_URL = "https://pcmap-api.place.naver.com/graphql"

# UserAgent 인스턴스 생성
ua = UserAgent()

def kill_existing_browsers():
    """기존 브라우저 프로세스 종료 - Ubuntu 최적화"""
    try:
        # Ubuntu/Linux 환경에서 브라우저 프로세스 종료
        subprocess.run(['pkill', '-f', 'chrome'], 
                     capture_output=True, check=False)
        subprocess.run(['pkill', '-f', 'chromium'], 
                     capture_output=True, check=False)
        subprocess.run(['pkill', '-f', 'google-chrome'], 
                     capture_output=True, check=False)
        subprocess.run(['pkill', '-f', 'chromium-browser'], 
                     capture_output=True, check=False)
        print("Existing browser processes cleaned up")
    except Exception as e:
        print(f"Error cleaning up browser processes: {e}")

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

async def get_real_browser_headers():
    print("Initializing headers/cookies...")
    """Get headers and cookies by accessing Naver Map with Playwright - retry until success with 3s timeout"""
    
    while True:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=ua.random
                )
                
                page = await context.new_page()
                await page.goto('https://map.naver.com/', timeout=5000)
                
                headers = await page.evaluate("""
                    () => ({
                        'accept': '*/*',
                        'accept-language': 'ko-KR,ko;q=0.9,en;q=0.8',
                        'content-type': 'application/json',
                        'user-agent': navigator.userAgent,
                        'referer': 'https://map.naver.com/',
                        'origin': 'https://map.naver.com'
                    })
                """)
                
                cookies = {cookie['name']: cookie['value'] for cookie in await context.cookies()}
                await browser.close()
                
                return headers, cookies
                
        except Exception as e:
            print(f"Browser header generation failed: {e} - Retrying...")
            continue

def test_requests_with_real_headers(num_requests=10):
    """Test requests with real browser headers - retry until 200"""
    success_count = 0
    
    # Clean up existing browser processes before starting
    print("Starting program - cleaning up existing browser processes...")
    kill_existing_browsers()
    
    headers, cookies = asyncio.run(get_real_browser_headers())
    
    for i in range(num_requests):
        retry_count = 0
        while True:
            retry_count += 1
            
            with requests.Session() as session:
                for name, value in cookies.items():
                    session.cookies.set(name, value)
                
                try:
                    response = session.post(GRAPHQL_URL, headers=headers, json=BODY, verify=False, timeout=5)
                    # time.sleep(.4)
                    # time.sleep(.5)
                    time.sleep(2)
                    
                    if response.status_code == 200:
                        success_count += 1
                        print(f"Request {i+1}: Success (200) - {retry_count}th attempt")
                        break
                    else:
                        print(f"Request {i+1}: Failed ({response.status_code}) - Restarting after browser cleanup...")
                        # kill_existing_browsers()
                        headers, cookies = asyncio.run(get_real_browser_headers())
                        
                except Exception as e:
                    print(f"Request {i+1}: Exception ({str(e)}) - {retry_count}th attempt, restarting after browser cleanup...")
                    # kill_existing_browsers()
                    headers, cookies = asyncio.run(get_real_browser_headers())
    
    print(f"\n=== Results ===")
    print(f"Total requests: {num_requests} | Success: {success_count} | Failed: {num_requests - success_count}")
    print(f"Success rate: {(success_count/num_requests)*100:.1f}%")

if __name__ == "__main__":
    test_requests_with_real_headers(num_requests=100000)
