import requests
import urllib3
import time

# HTTPS 인증 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def get_headers():
    """기본 헤더 반환"""
    return {
        'accept': '*/*',
        'accept-language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://map.naver.com/',
        'origin': 'https://map.naver.com'
    }

def test_requests_with_headers(num_requests=10):
    """기본 헤더로 requests 테스트"""
    success_count = 0
    
    print("프로그램 시작...")
    headers = get_headers()
    
    for i in range(num_requests):
        retry_count = 0
        while True:
            retry_count += 1
            
            try:
                response = requests.post(GRAPHQL_URL, headers=headers, json=BODY, verify=False, timeout=2)
                time.sleep(1)
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"요청 {i+1}: 성공 (200) - {retry_count}번째 시도")
                    break
                else:
                    print(f"요청 {i+1}: 실패 ({response.status_code}) - 재시도 중...")
                    if retry_count >= 3:  # 최대 3번 재시도
                        print(f"요청 {i+1}: 최대 재시도 횟수 초과")
                        break
                        
            except Exception as e:
                print(f"요청 {i+1}: 예외 ({str(e)}) - {retry_count}번째 시도")
                if retry_count >= 3:  # 최대 3번 재시도
                    print(f"요청 {i+1}: 최대 재시도 횟수 초과")
                    break
    
    print(f"\n=== 결과 ===")
    print(f"총 요청: {num_requests} | 성공: {success_count} | 실패: {num_requests - success_count}")
    print(f"성공률: {(success_count/num_requests)*100:.1f}%")

if __name__ == "__main__":
    test_requests_with_headers(num_requests=100000)
