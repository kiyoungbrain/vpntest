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

data = {
    "operationName": "getRestaurants",
    "variables": {},
    "query": """
    query getRestaurants {
      restaurants: restaurantList(input: {query: "서울"}) {
        items {
          id
          name
          x
          y
        }
        total
      }
    }
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
        
        # Generate random x-wtm-graphql value each time
        x_wtm_graphql = generate_random_wtm()
        headers["x-wtm-graphql"] = x_wtm_graphql
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"Request {count} - 200 | IP: {current_ip}")
            count += 1  # Only count 200 success
        else:
            print(f"Request {count} - {response.status_code} | IP: {current_ip}")
            # Don't count 429 errors
            
    except:
        pass  # Silently skip on error (don't count)
    
    time.sleep(0.1)  # 0.1s delay for Ctrl+C processing