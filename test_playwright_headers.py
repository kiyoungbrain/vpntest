import requests
import json
import base64
import random
import time
import uuid
import hashlib
import os
import platform
from datetime import datetime

# 각 컴퓨터별 고유 식별자 생성 (MAC 주소 기반)
def get_machine_id():
    """Generate unique machine identifier."""
    try:
        import platform
        import subprocess
        
        if platform.system() == "Windows":
            result = subprocess.run(['wmic', 'csproduct', 'get', 'uuid'], 
                                  capture_output=True, text=True, check=True)
            uuid_str = result.stdout.split('\n')[1].strip()
            return hashlib.md5(uuid_str.encode()).hexdigest()[:8]
        elif platform.system() == "Linux":
            # Ubuntu/Linux - /etc/machine-id 사용
            try:
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
                    return hashlib.md5(machine_id.encode()).hexdigest()[:8]
            except:
                # /etc/machine-id가 없으면 /var/lib/dbus/machine-id 시도
                try:
                    with open('/var/lib/dbus/machine-id', 'r') as f:
                        machine_id = f.read().strip()
                        return hashlib.md5(machine_id.encode()).hexdigest()[:8]
                except:
                    # CPU 정보로 대체
                    try:
                        result = subprocess.run(['cat', '/proc/cpuinfo'], 
                                              capture_output=True, text=True, check=True)
                        cpu_info = result.stdout
                        # CPU 정보에서 고유한 부분 추출
                        cpu_hash = hashlib.md5(cpu_info.encode()).hexdigest()[:8]
                        return cpu_hash
                    except:
                        pass
        else:
            # macOS
            try:
                with open('/etc/machine-id', 'r') as f:
                    return hashlib.md5(f.read().strip().encode()).hexdigest()[:8]
            except:
                pass
    except:
        pass
    
    # 모든 방법이 실패하면 랜덤 ID 생성
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8]

MACHINE_ID = get_machine_id()
print(f"Machine ID: {MACHINE_ID}")

# ExpressVPN 사용 - 프록시 없음

url = "https://pcmap-api.place.naver.com/graphql"

# 다양한 User-Agent 목록
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/139.0.0.0 Safari/537.36",
]

# 다양한 브라우저별 sec-ch-ua 값
SEC_CH_UA_VALUES = [
    '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    '"Not;A=Brand";v="99", "Google Chrome";v="138", "Chromium";v="138"',
    '"Not;A=Brand";v="99", "Google Chrome";v="137", "Chromium";v="137"',
    '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    '"Not;A=Brand";v="99", "Microsoft Edge";v="139", "Chromium";v="139"',
]

def get_random_headers():
    """Generate random headers for each request."""
    user_agent = random.choice(USER_AGENTS)
    sec_ch_ua = random.choice(SEC_CH_UA_VALUES)
    
    # User-Agent에 따라 플랫폼 결정
    if "Windows" in user_agent:
        platform = '"Windows"'
    elif "Macintosh" in user_agent:
        platform = '"macOS"'
    else:
        platform = '"Linux"'
    
    return {
        "accept": "*/*",
        "accept-language": random.choice(["ko", "ko-KR", "ko-KR,ko;q=0.9,en;q=0.8"]),
        "content-type": "application/json",
        "priority": random.choice(["u=1, i", "u=1", "i"]),
        "user-agent": user_agent,
        "sec-ch-ua": sec_ch_ua,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": platform,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "x-ncaptcha-violation": "false",
        "x-wtm-graphql": "",
        "x-machine-id": MACHINE_ID,  # 각 컴퓨터별 고유 식별자
    }


def generate_random_wtm():
    """Generate random x-wtm-graphql value."""
    # Use original format but with random values
    random_data = {
        "arg": f"random{random.randint(1000, 9999)}",
        "type": "restaurant", 
        "source": "place"
    }
    # Convert JSON to string then base64 encode
    json_str = json.dumps(random_data, separators=(',', ':'))
    return base64.b64encode(json_str.encode()).decode()

def get_current_ip():
    """Get current public IP address."""
    # 여러 IP 확인 서비스 시도 (ExpressVPN 사용 시 안정성 향상)
    ip_services = [
        "https://ifconfig.me",
        "https://api.ipify.org",
        "https://ipinfo.io/ip",
        "https://checkip.amazonaws.com"
    ]
    
    for service in ip_services:
        try:
            response = requests.get(service, timeout=5)
            if response.status_code == 200:
                return response.text.strip()
        except:
            continue
    
    return "Unknown"

def get_natural_delay():
    """Generate natural delay pattern."""
    # 다양한 지연 패턴 (초 단위)
    patterns = [
        random.uniform(0.05, 0.3),  # 빠른 요청
        random.uniform(0.3, 0.8),   # 보통 요청
        random.uniform(0.8, 2.0),   # 느린 요청
        random.uniform(2.0, 5.0),   # 매우 느린 요청 (가끔)
    ]
    
    # 가중치를 두어 대부분은 빠른-보통 패턴
    weights = [0.4, 0.4, 0.15, 0.05]
    return random.choices(patterns, weights=weights)[0]

def create_session():
    """Create a new session with cookies."""
    session = requests.Session()
    
    # 랜덤한 쿠키 설정
    cookies = {
        'NID_AUT': f"random{random.randint(100000, 999999)}",
        'NID_SES': f"session{random.randint(100000, 999999)}",
        'NID_JKL': f"jkl{random.randint(1000, 9999)}",
    }
    
    for name, value in cookies.items():
        session.cookies.set(name, value)
    
    return session

def get_random_query():
    """Generate random query with different cities."""
    cities = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "수원", "고양", "용인", "성남", "부천", "화성", "안산", "안양", "평택", "시흥", "김포", "의정부", "광명", "과천", "오산", "의왕", "이천", "안성", "하남", "여주", "양평", "동두천", "가평", "연천", "포천", "양주", "구리", "남양주", "파주"]
    
    city_english = {
        "서울": "Seoul", "부산": "Busan", "대구": "Daegu", "인천": "Incheon", "광주": "Gwangju", 
        "대전": "Daejeon", "울산": "Ulsan", "세종": "Sejong", "수원": "Suwon", "고양": "Goyang", 
        "용인": "Yongin", "성남": "Seongnam", "부천": "Bucheon", "화성": "Hwaseong", "안산": "Ansan", 
        "안양": "Anyang", "평택": "Pyeongtaek", "시흥": "Siheung", "김포": "Gimpo", "의정부": "Uijeongbu", 
        "광명": "Gwangmyeong", "과천": "Gwacheon", "오산": "Osan", "의왕": "Uiwang", "이천": "Icheon", 
        "안성": "Anseong", "하남": "Hanam", "여주": "Yeoju", "양평": "Yangpyeong", "동두천": "Dongducheon", 
        "가평": "Gapyeong", "연천": "Yeoncheon", "포천": "Pocheon", "양주": "Yangju", "구리": "Guri", 
        "남양주": "Namyangju", "파주": "Paju"
    }
    
    city = random.choice(cities)
    city_en = city_english.get(city, city)
    
    return {
        "operationName": "getRestaurants",
        "variables": {},
        "query": f"""
        query getRestaurants {{
          restaurants: restaurantList(input: {{query: "{city}"}}) {{
            items {{
              id
              name
              x
              y
            }}
            total
          }}
        }}
        """,
        "city_english": city_en
    }

# 세션 생성 (각 컴퓨터별로 고유한 세션)
session = create_session()

# 시작 시간 기록
start_time = datetime.now()
count = 1
error_count = 0
last_ip_check = 0

print(f"Starting requests with Machine ID: {MACHINE_ID}")
print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Platform: {platform.system()}")
print("=" * 50)
print("ExpressVPN 사용 시 주의사항:")
print("1. ExpressVPN이 연결되어 있는지 확인하세요")
print("2. 각 컴퓨터에서 다른 서버에 연결하세요")
print("3. 연결 상태: expressvpn status")
print("4. 서버 변경: expressvpn connect [서버명]")
print("=" * 50)

while True:
    try:
        # IP 주소는 10번에 한 번만 체크 (성능 최적화)
        if count % 10 == 1 or last_ip_check == 0:
            current_ip = get_current_ip()
            last_ip_check = count
        else:
            current_ip = "Cached"
        
        # 매번 새로운 헤더 생성
        headers = get_random_headers()
        
        # Generate random query and x-wtm-graphql value each time
        data = get_random_query()
        city_en = data["city_english"]
        x_wtm_graphql = generate_random_wtm()
        headers["x-wtm-graphql"] = x_wtm_graphql
        
        # ExpressVPN 사용 - 프록시 없이 직접 요청
        response = session.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            print(f"Request {count} - 200 | IP: {current_ip} | City: {city_en} | Machine: {MACHINE_ID}")
            count += 1  # 200 성공만 카운트
            error_count = 0  # 성공 시 에러 카운트 리셋
        else:
            error_count += 1
            print(f"Request {count} - {response.status_code} | IP: {current_ip} | City: {city_en} | Errors: {error_count}")
            
            # 연속 에러가 많으면 세션 재생성
            if error_count >= 5:
                print("Too many errors, recreating session...")
                session = create_session()
                error_count = 0
                time.sleep(random.uniform(2, 5))  # 에러 후 잠시 대기
            
    except Exception as e:
        error_count += 1
        print(f"Request {count} - Error: {str(e)[:50]}... | Errors: {error_count}")
        
        # 연속 에러가 많으면 세션 재생성
        if error_count >= 5:
            print("Too many errors, recreating session...")
            session = create_session()
            error_count = 0
            time.sleep(random.uniform(2, 5))  # 에러 후 잠시 대기
    
    # 자연스러운 지연 패턴 적용
    delay = get_natural_delay()
    time.sleep(delay)
    
    # 100번마다 통계 출력
    if count % 100 == 0:
        elapsed = datetime.now() - start_time
        print(f"=== Stats after {count} requests ===")
        print(f"Elapsed time: {elapsed}")
        print(f"Requests per minute: {count / (elapsed.total_seconds() / 60):.2f}")
        print(f"Machine ID: {MACHINE_ID}")
        print("=" * 40)