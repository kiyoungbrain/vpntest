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
        print("기존 브라우저 프로세스 정리 완료")
    except Exception as e:
        print(f"브라우저 프로세스 정리 중 오류: {e}")

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
    print("헤더/쿠키 초기화 중...")
    """Playwright로 실제 네이버 맵에 접속해서 헤더와 쿠키 가져오기 - 3초 타임아웃으로 될 때까지 재시도"""
    
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
                await page.goto('https://map.naver.com/', timeout=3000)
                
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
            print(f"브라우저 헤더 생성 실패: {e} - 재시도 중...")
            continue

def test_requests_with_real_headers(num_requests=10):
    """실제 브라우저 헤더로 requests 테스트 - 200이 될 때까지 재시도"""
    success_count = 0
    
    # 프로그램 시작 전 기존 브라우저 프로세스 정리
    print("프로그램 시작 - 기존 브라우저 프로세스 정리 중...")
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
                    response = session.post(GRAPHQL_URL, headers=headers, json=BODY, verify=False, timeout=2)
                    # time.sleep(.4)
                    time.sleep(.5)
                    
                    if response.status_code == 200:
                        success_count += 1
                        print(f"요청 {i+1}: 성공 (200) - {retry_count}번째 시도")
                        break
                    else:
                        print(f"요청 {i+1}: 실패 ({response.status_code}) - 브라우저 프로세스 정리 후 재시작...")
                        # kill_existing_browsers()
                        headers, cookies = asyncio.run(get_real_browser_headers())
                        
                except Exception as e:
                    print(f"요청 {i+1}: 예외 ({str(e)}) - {retry_count}번째 시도, 브라우저 프로세스 정리 후 재시작...")
                    # kill_existing_browsers()
                    headers, cookies = asyncio.run(get_real_browser_headers())
    
    print(f"\n=== 결과 ===")
    print(f"총 요청: {num_requests} | 성공: {success_count} | 실패: {num_requests - success_count}")
    print(f"성공률: {(success_count/num_requests)*100:.1f}%")

if __name__ == "__main__":
    test_requests_with_real_headers(num_requests=100000)
