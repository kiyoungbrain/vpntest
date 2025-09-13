import requests
import urllib3
import asyncio
import subprocess
import os
import random
import socket
from playwright.async_api import async_playwright
from fake_useragent import UserAgent
import time

# HTTPS 인증 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GRAPHQL_URL = "https://pcmap-api.place.naver.com/graphql"

# UserAgent 인스턴스 생성
ua = UserAgent()

# 컴퓨터별 고유 식별자 생성 (IP 기반)
def get_machine_id():
    """현재 컴퓨터의 고유 식별자 생성"""
    try:
        # 외부 IP 확인 (더 고유한 식별자)
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text.strip()
    except:
        # 실패시 로컬 IP 사용
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return f"{hostname}_{local_ip}"

MACHINE_ID = get_machine_id()
print(f"현재 컴퓨터 ID: {MACHINE_ID}")

def kill_existing_browsers():
    """기존 브라우저 프로세스 종료 - Windows/Linux 호환"""
    try:
        import platform
        system = platform.system().lower()
        
        if system == "windows":
            # Windows 환경
            subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], 
                         capture_output=True, check=False)
            subprocess.run(['taskkill', '/f', '/im', 'chromium.exe'], 
                         capture_output=True, check=False)
        else:
            # Linux/Ubuntu 환경
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
    print(f"[{MACHINE_ID}] 헤더/쿠키 초기화 중...")
    """Playwright로 실제 네이버 맵에 접속해서 헤더와 쿠키 가져오기 - 컴퓨터별 고유 세션"""
    
    while True:
        try:
            async with async_playwright() as p:
                # 컴퓨터별로 다른 뷰포트와 User-Agent 사용
                viewport_options = [
                    {'width': 1920, 'height': 1080},
                    {'width': 1366, 'height': 768},
                    {'width': 1440, 'height': 900},
                    {'width': 1536, 'height': 864}
                ]
                
                # 컴퓨터 ID 기반으로 일관된 뷰포트 선택
                viewport_idx = hash(MACHINE_ID) % len(viewport_options)
                selected_viewport = viewport_options[viewport_idx]
                
                # Windows/Linux 호환 데이터 디렉토리 경로
                import tempfile
                import os
                temp_dir = tempfile.gettempdir()
                user_data_dir = os.path.join(temp_dir, f'chrome_{MACHINE_ID[:8]}')
                
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding'
                    ]
                )
                
                context = await browser.new_context(
                    viewport=selected_viewport,
                    user_agent=ua.random,
                    locale='ko-KR',
                    timezone_id='Asia/Seoul'
                )
                
                page = await context.new_page()
                
                # 컴퓨터별로 다른 접근 경로 사용
                access_paths = [
                    'https://map.naver.com/',
                    'https://map.naver.com/v5/',
                    'https://map.naver.com/v5/search',
                    'https://map.naver.com/v5/restaurant'
                ]
                access_path = access_paths[hash(MACHINE_ID) % len(access_paths)]
                
                await page.goto(access_path, timeout=5000)
                
                # 페이지 로딩 대기
                await page.wait_for_timeout(random.randint(1000, 3000))
                
                headers = await page.evaluate("""
                    () => ({
                        'accept': '*/*',
                        'accept-language': 'ko-KR,ko;q=0.9,en;q=0.8',
                        'content-type': 'application/json',
                        'user-agent': navigator.userAgent,
                        'referer': window.location.href,
                        'origin': window.location.origin,
                        'x-requested-with': 'XMLHttpRequest'
                    })
                """)
                
                cookies = {cookie['name']: cookie['value'] for cookie in await context.cookies()}
                
                # 컴퓨터별 고유 식별자를 쿠키에 추가
                cookies[f'machine_id_{MACHINE_ID[:8]}'] = MACHINE_ID
                
                await browser.close()
                
                print(f"[{MACHINE_ID}] 브라우저 세션 생성 완료 - 뷰포트: {selected_viewport}")
                return headers, cookies
                
        except Exception as e:
            print(f"[{MACHINE_ID}] 브라우저 헤더 생성 실패: {e} - 재시도 중...")
            await asyncio.sleep(random.uniform(1, 3))  # 재시도 전 랜덤 대기
            continue

def test_requests_with_real_headers(num_requests=10):
    """실제 브라우저 헤더로 requests 테스트 - 컴퓨터별 분산 처리 최적화"""
    success_count = 0
    
    # 프로그램 시작 전 기존 브라우저 프로세스 정리
    print(f"[{MACHINE_ID}] 프로그램 시작 - 기존 브라우저 프로세스 정리 중...")
    kill_existing_browsers()
    
    # 컴퓨터별로 다른 초기 대기 시간 적용
    initial_delay = (hash(MACHINE_ID) % 10) * 0.5  # 0~4.5초 랜덤 대기
    print(f"[{MACHINE_ID}] 초기 대기: {initial_delay}초")
    time.sleep(initial_delay)
    
    headers, cookies = asyncio.run(get_real_browser_headers())
    
    # 컴퓨터별로 다른 요청 간격 설정
    base_delay = 0.3 + (hash(MACHINE_ID) % 5) * 0.1  # 0.3~0.7초
    print(f"[{MACHINE_ID}] 요청 간격: {base_delay}초")
    
    for i in range(num_requests):
        retry_count = 0
        while True:
            retry_count += 1
            
            with requests.Session() as session:
                for name, value in cookies.items():
                    session.cookies.set(name, value)
                
                try:
                    # 컴퓨터별로 다른 타임아웃 설정
                    timeout = 2 + (hash(MACHINE_ID) % 3)  # 2~4초
                    
                    response = session.post(GRAPHQL_URL, headers=headers, json=BODY, verify=False, timeout=timeout)
                    
                    if response.status_code == 200:
                        success_count += 1
                        print(f"[{MACHINE_ID}] 요청 {i+1}: 성공 (200) - {retry_count}번째 시도")
                        
                        # 성공 후 컴퓨터별 랜덤 대기
                        delay = base_delay + random.uniform(0, 0.2)
                        time.sleep(delay)
                        break
                        
                    elif response.status_code == 429:
                        print(f"[{MACHINE_ID}] 요청 {i+1}: Rate Limited (429) - {retry_count}번째 시도, 대기 후 재시도...")
                        # 429 에러시 더 긴 대기
                        time.sleep(random.uniform(2, 5))
                        headers, cookies = asyncio.run(get_real_browser_headers())
                        
                    else:
                        print(f"[{MACHINE_ID}] 요청 {i+1}: 실패 ({response.status_code}) - 브라우저 세션 갱신...")
                        headers, cookies = asyncio.run(get_real_browser_headers())
                        
                except Exception as e:
                    print(f"[{MACHINE_ID}] 요청 {i+1}: 예외 ({str(e)}) - {retry_count}번째 시도, 세션 갱신...")
                    time.sleep(random.uniform(1, 3))
                    headers, cookies = asyncio.run(get_real_browser_headers())
    
    print(f"\n=== [{MACHINE_ID}] 결과 ===")
    print(f"총 요청: {num_requests} | 성공: {success_count} | 실패: {num_requests - success_count}")
    print(f"성공률: {(success_count/num_requests)*100:.1f}%")

if __name__ == "__main__":
    test_requests_with_real_headers(num_requests=100000)
