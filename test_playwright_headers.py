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

async def get_real_browser_headers(session_id=None):
    """Playwright로 실제 네이버 맵에 접속해서 헤더와 쿠키 가져오기 - 세션별 고유 식별"""
    if session_id is None:
        session_id = f"{MACHINE_ID}_{int(time.time())}"
    
    print(f"[{MACHINE_ID}] 헤더/쿠키 초기화 중... (세션: {session_id[:12]})")
    
    while True:
        try:
            async with async_playwright() as p:
                # 세션별로 다른 뷰포트와 User-Agent 사용
                viewport_options = [
                    {'width': 1920, 'height': 1080},
                    {'width': 1366, 'height': 768},
                    {'width': 1440, 'height': 900},
                    {'width': 1536, 'height': 864},
                    {'width': 1280, 'height': 720},
                    {'width': 1600, 'height': 900}
                ]
                
                # 세션 ID 기반으로 뷰포트 선택 (더 다양하게)
                viewport_idx = hash(session_id) % len(viewport_options)
                selected_viewport = viewport_options[viewport_idx]
                
                # 세션별 고유 브라우저 설정
                browser_args = [
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-dev-shm-usage',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-extensions',
                    '--disable-sync',
                    '--disable-translate',
                    '--hide-scrollbars',
                    '--mute-audio',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-software-rasterizer'
                ]
                
                # 세션별로 다른 추가 인자
                if hash(session_id) % 2 == 0:
                    browser_args.extend(['--disable-background-networking', '--disable-background-timer-throttling'])
                else:
                    browser_args.extend(['--disable-client-side-phishing-detection', '--disable-hang-monitor'])
                
                browser = await p.chromium.launch(
                    headless=True,
                    args=browser_args
                )
                
                # 세션별 고유 컨텍스트 설정
                context_options = {
                    'viewport': selected_viewport,
                    'user_agent': ua.random,
                    'locale': 'ko-KR',
                    'timezone_id': 'Asia/Seoul',
                    'extra_http_headers': {
                        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }
                }
                
                context = await browser.new_context(**context_options)
                page = await context.new_page()
                
                # 세션별로 다른 접근 시나리오
                access_scenarios = [
                    # 시나리오 1: 메인 페이지에서 시작
                    ['https://map.naver.com/', 'https://map.naver.com/v5/'],
                    # 시나리오 2: 검색 페이지에서 시작  
                    ['https://map.naver.com/v5/search', 'https://map.naver.com/v5/'],
                    # 시나리오 3: 레스토랑 페이지에서 시작
                    ['https://map.naver.com/v5/restaurant', 'https://map.naver.com/'],
                    # 시나리오 4: 직접 API 페이지
                    ['https://map.naver.com/v5/', 'https://map.naver.com/v5/search']
                ]
                
                scenario_idx = hash(session_id) % len(access_scenarios)
                scenario = access_scenarios[scenario_idx]
                
                # 여러 페이지를 순차적으로 방문 (더 자연스러운 브라우징)
                for i, url in enumerate(scenario):
                    await page.goto(url, timeout=5000)
                    await page.wait_for_timeout(random.randint(500, 1500))
                    
                    # 페이지에서 랜덤한 동작 수행 (마우스 이동, 스크롤 등)
                    if i == 0:  # 첫 페이지에서만
                        await page.mouse.move(random.randint(100, 800), random.randint(100, 600))
                        await page.evaluate("window.scrollTo(0, Math.random() * 500)")
                        await page.wait_for_timeout(random.randint(200, 800))
                
                # 최종 헤더 수집
                headers = await page.evaluate("""
                    () => ({
                        'accept': '*/*',
                        'accept-language': 'ko-KR,ko;q=0.9,en;q=0.8',
                        'accept-encoding': 'gzip, deflate, br',
                        'content-type': 'application/json',
                        'user-agent': navigator.userAgent,
                        'referer': window.location.href,
                        'origin': window.location.origin,
                        'x-requested-with': 'XMLHttpRequest',
                        'cache-control': 'no-cache',
                        'pragma': 'no-cache'
                    })
                """)
                
                cookies = {cookie['name']: cookie['value'] for cookie in await context.cookies()}
                
                # 세션별 고유 식별자를 쿠키에 추가
                cookies[f'session_{session_id[:8]}'] = session_id
                cookies[f'machine_{MACHINE_ID[:8]}'] = MACHINE_ID
                cookies[f'timestamp_{int(time.time())}'] = str(int(time.time()))
                
                await browser.close()
                
                print(f"[{MACHINE_ID}] 브라우저 세션 생성 완료 - 뷰포트: {selected_viewport}, 시나리오: {scenario_idx}")
                return headers, cookies
                
        except Exception as e:
            print(f"[{MACHINE_ID}] 브라우저 헤더 생성 실패: {e} - 재시도 중...")
            await asyncio.sleep(random.uniform(2, 5))  # 재시도 전 더 긴 대기
            continue

def test_requests_with_real_headers(num_requests=10):
    """실제 브라우저 헤더로 requests 테스트 - 안정적인 세션 로테이션으로 429 우회"""
    success_count = 0
    consecutive_failures = 0
    max_consecutive_failures = 5  # 연속 실패 제한
    
    # 프로그램 시작 전 기존 브라우저 프로세스 정리
    print(f"[{MACHINE_ID}] 프로그램 시작 - 기존 브라우저 프로세스 정리 중...")
    kill_existing_browsers()
    
    # 컴퓨터별로 다른 초기 대기 시간 적용
    initial_delay = (hash(MACHINE_ID) % 10) * 0.5  # 0~4.5초 랜덤 대기
    print(f"[{MACHINE_ID}] 초기 대기: {initial_delay}초")
    time.sleep(initial_delay)
    
    # 컴퓨터별로 다른 요청 간격 설정
    base_delay = 0.5 + (hash(MACHINE_ID) % 3) * 0.2  # 0.5~1.1초 (더 느리게)
    print(f"[{MACHINE_ID}] 요청 간격: {base_delay}초")
    
    # 세션 로테이션을 위한 카운터
    session_refresh_interval = 20 + (hash(MACHINE_ID) % 10)  # 20~29번마다 세션 갱신
    print(f"[{MACHINE_ID}] 세션 갱신 주기: {session_refresh_interval}번")
    
    headers, cookies = None, None
    last_success_time = time.time()
    
    try:
        for i in range(num_requests):
            retry_count = 0
            request_start_time = time.time()
            
            # 진행 상황 출력 (100번마다)
            if (i + 1) % 100 == 0:
                elapsed_time = time.time() - last_success_time
                print(f"[{MACHINE_ID}] 진행 상황: {i+1}/{num_requests} (성공: {success_count}, 연속실패: {consecutive_failures})")
            
            # 세션 갱신 조건: 첫 요청, 주기적 갱신, 또는 429 에러 후
            should_refresh_session = (
                headers is None or 
                (i + 1) % session_refresh_interval == 0 or
                retry_count > 0 or
                consecutive_failures >= 3  # 연속 실패시 세션 갱신
            )
            
            if should_refresh_session:
                print(f"[{MACHINE_ID}] 세션 갱신 중... ({i+1}번째 요청)")
                try:
                    headers, cookies = asyncio.run(get_real_browser_headers())
                    consecutive_failures = 0  # 세션 갱신 성공시 실패 카운터 리셋
                    # 세션 갱신 후 추가 대기
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    print(f"[{MACHINE_ID}] 세션 갱신 실패: {e} - 브라우저 프로세스 정리 후 재시도...")
                    kill_existing_browsers()
                    time.sleep(random.uniform(3, 7))
                    continue
            
            while retry_count < 10:  # 최대 10번 재시도
                retry_count += 1
                
                try:
                    with requests.Session() as session:
                        for name, value in cookies.items():
                            session.cookies.set(name, value)
                        
                        # 컴퓨터별로 다른 타임아웃 설정
                        timeout = 5 + (hash(MACHINE_ID) % 3)  # 5~7초 (더 길게)
                        
                        response = session.post(GRAPHQL_URL, headers=headers, json=BODY, verify=False, timeout=timeout)
                        
                        if response.status_code == 200:
                            success_count += 1
                            consecutive_failures = 0  # 성공시 실패 카운터 리셋
                            last_success_time = time.time()
                            
                            print(f"[{MACHINE_ID}] 요청 {i+1}: 성공 (200) - {retry_count}번째 시도")
                            
                            # 성공 후 컴퓨터별 랜덤 대기
                            delay = base_delay + random.uniform(0, 0.5)
                            time.sleep(delay)
                            break
                            
                        elif response.status_code == 429:
                            print(f"[{MACHINE_ID}] 요청 {i+1}: Rate Limited (429) - {retry_count}번째 시도, 세션 갱신 후 대기...")
                            consecutive_failures += 1
                            
                            # 429 에러시 세션 갱신 후 더 긴 대기
                            try:
                                headers, cookies = asyncio.run(get_real_browser_headers())
                                time.sleep(random.uniform(5, 10))  # 5~10초 대기
                            except Exception as e:
                                print(f"[{MACHINE_ID}] 429 후 세션 갱신 실패: {e}")
                                time.sleep(random.uniform(10, 20))  # 더 긴 대기
                            
                        else:
                            print(f"[{MACHINE_ID}] 요청 {i+1}: 실패 ({response.status_code}) - {retry_count}번째 시도")
                            consecutive_failures += 1
                            
                            if retry_count < 5:  # 5번 이하일 때만 세션 갱신
                                try:
                                    headers, cookies = asyncio.run(get_real_browser_headers())
                                    time.sleep(random.uniform(2, 4))
                                except Exception as e:
                                    print(f"[{MACHINE_ID}] 세션 갱신 실패: {e}")
                                    time.sleep(random.uniform(5, 10))
                            
                    # 요청 시간이 너무 오래 걸리면 중단
                    if time.time() - request_start_time > 60:  # 1분 이상 걸리면
                        print(f"[{MACHINE_ID}] 요청 {i+1}: 타임아웃 (60초 초과) - 다음 요청으로 이동")
                        break
                        
                except requests.exceptions.Timeout:
                    print(f"[{MACHINE_ID}] 요청 {i+1}: 타임아웃 - {retry_count}번째 시도")
                    consecutive_failures += 1
                    time.sleep(random.uniform(2, 5))
                    
                except requests.exceptions.ConnectionError:
                    print(f"[{MACHINE_ID}] 요청 {i+1}: 연결 오류 - {retry_count}번째 시도")
                    consecutive_failures += 1
                    time.sleep(random.uniform(3, 8))
                    
                except Exception as e:
                    print(f"[{MACHINE_ID}] 요청 {i+1}: 예외 ({str(e)}) - {retry_count}번째 시도")
                    consecutive_failures += 1
                    time.sleep(random.uniform(2, 5))
            
            # 연속 실패가 너무 많으면 긴 대기
            if consecutive_failures >= max_consecutive_failures:
                print(f"[{MACHINE_ID}] 연속 실패 {consecutive_failures}회 - 30초 대기 후 계속...")
                time.sleep(30)
                consecutive_failures = 0  # 대기 후 리셋
            
            # 전체 진행 시간이 너무 오래 걸리면 중단
            if time.time() - last_success_time > 300:  # 5분간 성공이 없으면
                print(f"[{MACHINE_ID}] 5분간 성공 없음 - 프로그램 중단")
                break
                
    except KeyboardInterrupt:
        print(f"\n[{MACHINE_ID}] 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n[{MACHINE_ID}] 예상치 못한 오류: {e}")
    finally:
        # 마지막에 브라우저 프로세스 정리
        print(f"[{MACHINE_ID}] 프로그램 종료 - 브라우저 프로세스 정리 중...")
        kill_existing_browsers()
    
    print(f"\n=== [{MACHINE_ID}] 최종 결과 ===")
    print(f"총 요청: {i+1} | 성공: {success_count} | 실패: {i+1 - success_count}")
    print(f"성공률: {(success_count/(i+1))*100:.1f}%")
    print(f"연속 실패 최대: {consecutive_failures}회")

if __name__ == "__main__":
    test_requests_with_real_headers(num_requests=100000)
