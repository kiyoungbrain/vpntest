import requests
import urllib3
import asyncio
import subprocess
import os
import random
import socket
import hashlib
from playwright.async_api import async_playwright
from fake_useragent import UserAgent
import time

# HTTPS 인증 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GRAPHQL_URL = "https://pcmap-api.place.naver.com/graphql"

# UserAgent 인스턴스 생성
ua = UserAgent()

# 다양한 User-Agent 풀 생성
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15"
]

# 다양한 Accept-Language 옵션
ACCEPT_LANGUAGES = [
    "ko-KR,ko;q=0.9,en;q=0.8",
    "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "ko-KR,ko;q=0.8,en;q=0.9",
    "ko,ko-KR;q=0.9,en;q=0.8",
    "ko-KR,ko;q=0.9,ja;q=0.8,en;q=0.7"
]

# 다양한 뷰포트 크기
VIEWPORTS = [
    {'width': 1920, 'height': 1080},
    {'width': 1366, 'height': 768},
    {'width': 1440, 'height': 900},
    {'width': 1536, 'height': 864},
    {'width': 1280, 'height': 720},
    {'width': 1600, 'height': 900}
]

def get_machine_id():
    """컴퓨터별 고유 ID 생성"""
    try:
        # 호스트명과 MAC 주소를 조합해서 고유 ID 생성
        hostname = socket.gethostname()
        mac = ':'.join(['{:02x}'.format((random.getrandbits(8) << 8) + random.getrandbits(8)) for _ in range(6)])
        return hashlib.md5(f"{hostname}_{mac}".encode()).hexdigest()[:8]
    except:
        return f"machine_{random.randint(1000, 9999)}"

def get_proxy_list():
    """프록시 리스트 반환 (실제 사용 시 프록시 서버 정보를 입력하세요)"""
    # 실제 프록시 서버가 있다면 여기에 추가
    # 예시: ["http://proxy1:port", "http://proxy2:port", "socks5://proxy3:port"]
    return []

def get_random_proxy():
    """랜덤한 프록시 선택"""
    proxy_list = get_proxy_list()
    if proxy_list:
        return random.choice(proxy_list)
    return None

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

def get_random_headers():
    """랜덤한 헤더 생성"""
    user_agent = random.choice(USER_AGENTS)
    accept_language = random.choice(ACCEPT_LANGUAGES)
    
    # 다양한 Accept 옵션
    accepts = [
        '*/*',
        'application/json, text/plain, */*',
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'application/json, text/javascript, */*; q=0.01'
    ]
    
    # 다양한 Referer 옵션
    referers = [
        'https://map.naver.com/',
        'https://map.naver.com',
        'https://www.naver.com/',
        'https://www.naver.com'
    ]
    
    headers = {
        'accept': random.choice(accepts),
        'accept-language': accept_language,
        'content-type': 'application/json',
        'user-agent': user_agent,
        'referer': random.choice(referers),
        'origin': 'https://map.naver.com',
        'accept-encoding': 'gzip, deflate, br',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-ch-ua': f'"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': f'"{random.choice(["Windows", "macOS", "Linux"])}"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin'
    }
    
    return headers

async def get_real_browser_headers():
    print("헤더/쿠키 초기화 중...")
    """Playwright로 실제 네이버 맵에 접속해서 헤더와 쿠키 가져오기 - 3초 타임아웃으로 될 때까지 재시도"""
    
    machine_id = get_machine_id()
    print(f"머신 ID: {machine_id}")
    
    while True:
        try:
            async with async_playwright() as p:
                # 랜덤한 User-Agent와 뷰포트 선택
                user_agent = random.choice(USER_AGENTS)
                viewport = random.choice(VIEWPORTS)
                
                # 프록시 설정
                proxy = get_random_proxy()
                browser_args = [
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-extensions',
                    f'--user-agent={user_agent}'
                ]
                
                if proxy:
                    print(f"프록시 사용: {proxy}")
                    browser_args.append(f'--proxy-server={proxy}')
                
                browser = await p.chromium.launch(
                    headless=True,
                    args=browser_args
                )
                
                context = await browser.new_context(
                    viewport=viewport,
                    user_agent=user_agent,
                    locale='ko-KR',
                    timezone_id='Asia/Seoul'
                )
                
                page = await context.new_page()
                
                # 랜덤한 대기 시간
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                await page.goto('https://map.naver.com/', timeout=5000)
                
                # 페이지 로딩 후 추가 대기
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                # 동적으로 헤더 생성
                headers = await page.evaluate("""
                    () => {
                        const acceptLanguages = [
                            'ko-KR,ko;q=0.9,en;q=0.8',
                            'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                            'ko-KR,ko;q=0.8,en;q=0.9'
                        ];
                        const accepts = [
                            '*/*',
                            'application/json, text/plain, */*',
                            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                        ];
                        const referers = [
                            'https://map.naver.com/',
                            'https://map.naver.com',
                            'https://www.naver.com/'
                        ];
                        
                        return {
                            'accept': accepts[Math.floor(Math.random() * accepts.length)],
                            'accept-language': acceptLanguages[Math.floor(Math.random() * acceptLanguages.length)],
                            'content-type': 'application/json',
                            'user-agent': navigator.userAgent,
                            'referer': referers[Math.floor(Math.random() * referers.length)],
                            'origin': 'https://map.naver.com',
                            'accept-encoding': 'gzip, deflate, br',
                            'cache-control': 'no-cache',
                            'pragma': 'no-cache'
                        };
                    }
                """)
                
                cookies = {cookie['name']: cookie['value'] for cookie in await context.cookies()}
                await browser.close()
                
                print(f"새로운 헤더 생성 완료 - User-Agent: {headers['user-agent'][:50]}...")
                return headers, cookies
                
        except Exception as e:
            print(f"브라우저 헤더 생성 실패: {e} - 재시도 중...")
            await asyncio.sleep(random.uniform(1.0, 3.0))
            continue

def test_requests_with_real_headers(num_requests=10):
    """실제 브라우저 헤더로 requests 테스트 - 200이 될 때까지 재시도"""
    success_count = 0
    failure_count = 0
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    # 프로그램 시작 전 기존 브라우저 프로세스 정리
    print("프로그램 시작 - 기존 브라우저 프로세스 정리 중...")
    kill_existing_browsers()
    
    # 머신 ID 출력
    machine_id = get_machine_id()
    print(f"머신 ID: {machine_id}")
    
    headers, cookies = asyncio.run(get_real_browser_headers())
    
    for i in range(num_requests):
        retry_count = 0
        request_success = False
        
        while retry_count < 10:  # 최대 10번 재시도
            retry_count += 1
            
            with requests.Session() as session:
                for name, value in cookies.items():
                    session.cookies.set(name, value)
                
                # 프록시 설정
                proxy = get_random_proxy()
                proxies = None
                if proxy:
                    proxies = {
                        'http': proxy,
                        'https': proxy
                    }
                
                try:
                    # 랜덤한 대기 시간 (0.3초 ~ 1.5초)
                    sleep_time = random.uniform(0.3, 1.5)
                    time.sleep(sleep_time)
                    
                    response = session.post(GRAPHQL_URL, headers=headers, json=BODY, verify=False, timeout=5, proxies=proxies)
                    
                    if response.status_code == 200:
                        success_count += 1
                        consecutive_failures = 0
                        request_success = True
                        print(f"요청 {i+1}: 성공 (200) - {retry_count}번째 시도 - 머신: {machine_id}")
                        break
                    elif response.status_code == 429:
                        print(f"요청 {i+1}: Rate Limited (429) - {retry_count}번째 시도 - 머신: {machine_id}")
                        # 429 에러 시 더 긴 대기 시간
                        time.sleep(random.uniform(2.0, 5.0))
                        consecutive_failures += 1
                        
                        # 연속 실패가 많으면 헤더 재생성
                        if consecutive_failures >= 3:
                            print("연속 실패로 인한 헤더 재생성...")
                            headers, cookies = asyncio.run(get_real_browser_headers())
                            consecutive_failures = 0
                    else:
                        print(f"요청 {i+1}: 실패 ({response.status_code}) - {retry_count}번째 시도 - 머신: {machine_id}")
                        consecutive_failures += 1
                        
                        # 연속 실패가 많으면 헤더 재생성
                        if consecutive_failures >= 3:
                            print("연속 실패로 인한 헤더 재생성...")
                            headers, cookies = asyncio.run(get_real_browser_headers())
                            consecutive_failures = 0
                        
                        # 백오프 전략: 실패할수록 더 긴 대기
                        backoff_time = min(2 ** retry_count, 30)  # 최대 30초
                        time.sleep(random.uniform(backoff_time * 0.5, backoff_time))
                        
                except Exception as e:
                    print(f"요청 {i+1}: 예외 ({str(e)}) - {retry_count}번째 시도 - 머신: {machine_id}")
                    consecutive_failures += 1
                    
                    # 연속 실패가 많으면 헤더 재생성
                    if consecutive_failures >= 3:
                        print("연속 실패로 인한 헤더 재생성...")
                        headers, cookies = asyncio.run(get_real_browser_headers())
                        consecutive_failures = 0
                    
                    # 백오프 전략
                    backoff_time = min(2 ** retry_count, 30)
                    time.sleep(random.uniform(backoff_time * 0.5, backoff_time))
        
        if not request_success:
            failure_count += 1
            print(f"요청 {i+1}: 최종 실패 - 머신: {machine_id}")
        
        # 주기적으로 헤더 갱신 (매 20번째 요청마다)
        if (i + 1) % 20 == 0:
            print(f"주기적 헤더 갱신 - {i+1}번째 요청 후")
            headers, cookies = asyncio.run(get_real_browser_headers())
    
    print(f"\n=== 결과 (머신: {machine_id}) ===")
    print(f"총 요청: {num_requests} | 성공: {success_count} | 실패: {failure_count}")
    print(f"성공률: {(success_count/num_requests)*100:.1f}%")

if __name__ == "__main__":
    test_requests_with_real_headers(num_requests=100000)
