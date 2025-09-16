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
    """Return basic headers"""
    return {
        'accept': '*/*',
        'accept-language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://map.naver.com/',
        'origin': 'https://map.naver.com'
    }

def test_requests_with_headers(num_requests=10):
    """Test requests with basic headers"""
    success_count = 0
    
    headers = get_headers()
    
    for i in range(num_requests):
        retry_count = 0
        while True:
            retry_count += 1
            
            try:
                response = requests.post(GRAPHQL_URL, headers=headers, json=BODY, verify=False, timeout=2)
                time.sleep(1.5)
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"Request {i+1}: 200")
                    break
                elif response.status_code == 429:
                    print(f"Request {i+1}: 429 - Waiting 15 seconds...")
                    time.sleep(15)
                else:
                    print(f"Request {i+1}: {response.status_code}")
                        
            except Exception as e:
                print(f"Request {i+1}: ERROR")
    
    print(f"\n=== Results ===")
    print(f"Total requests: {num_requests} | Success: {success_count} | Failed: {num_requests - success_count}")
    print(f"Success rate: {(success_count/num_requests)*100:.1f}%")

if __name__ == "__main__":
    test_requests_with_headers(num_requests=100000)
