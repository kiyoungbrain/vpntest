import requests
import urllib3
import time
import random
import subprocess
import re

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

def get_network_interface():
    """Get the main network interface name"""
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True, check=True)
        interface = result.stdout.split()[4]  # Get interface name from default route
        return interface
    except:
        return 'eth0'  # Default fallback

def generate_random_mac():
    """Generate a random MAC address"""
    return ':'.join(['%02x' % random.randint(0, 255) for _ in range(6)])

def change_mac_address():
    """Change MAC address of the network interface"""
    interface = get_network_interface()
    new_mac = generate_random_mac()
    
    try:
        # Bring interface down
        subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', interface, 'down'], 
                      check=True, capture_output=True)
        
        # Change MAC address
        subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', interface, 'address', new_mac], 
                      check=True, capture_output=True)
        
        # Bring interface up
        subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', interface, 'up'], 
                      check=True, capture_output=True)
        
        print(f"MAC address changed to: {new_mac}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to change MAC address: {e}")
        return False

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
        
        # Change MAC address before each request
        print(f"Request {i+1}: Changing MAC address...")
        change_mac_address()
        time.sleep(2)  # Wait for network to stabilize
        
        while True:
            retry_count += 1
            
            try:
                response = requests.post(GRAPHQL_URL, headers=headers, json=BODY, verify=False, timeout=2)
                # time.sleep(1.5)
                
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
