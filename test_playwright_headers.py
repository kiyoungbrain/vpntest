import requests
import json
import base64
import random
import time

url = "https://pcmap-api.place.naver.com/graphql"

headers = {
    "accept": "*/*",
    "accept-language": "ko",
    "content-type": "application/json",
    "priority": "u=1, i",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "x-ncaptcha-violation": "false",
    "x-wtm-graphql": "",
}

def get_random_query():
    """Generate random query with different cities."""
    cities = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "수원", "고양", "용인", "성남", "부천", "화성", "안산", "안양", "평택", "시흥", "김포", "의정부", "광명", "과천", "오산", "의왕", "이천", "안성", "하남", "여주", "양평", "동두천", "가평", "연천", "포천", "양주", "구리", "남양주", "파주", "고양", "의정부", "동두천", "가평", "연천", "포천", "양주", "구리", "남양주", "파주"]
    
    city = random.choice(cities)
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
        """
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
    try:
        response = requests.get("https://ifconfig.me", timeout=5)
        return response.text.strip()
    except:
        return "Unknown"

count = 1
while True:
    try:
        # Get current IP
        current_ip = get_current_ip()
        
        # Generate random query and x-wtm-graphql value each time
        data = get_random_query()
        city = data["query"].split('query: "')[1].split('"')[0]  # Extract city from query
        x_wtm_graphql = generate_random_wtm()
        headers["x-wtm-graphql"] = x_wtm_graphql
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"Request {count} - 200 | IP: {current_ip} | City: {city}")
            count += 1  # 200 성공만 카운트
        else:
            print(f"Request {count} - {response.status_code} | IP: {current_ip} | City: {city}")
            # 429 등 에러는 카운트 안함
            
    except:
        pass  # 에러 발생 시 조용히 넘어가기 (카운트 안함)
    
    time.sleep(.1)