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
    """Generate a random MAC address by changing only the last character"""
    # Get current MAC address as base
    try:
        interface = get_network_interface()
        result = subprocess.run(['ip', 'link', 'show', interface], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            # Extract current MAC address
            mac_match = re.search(r'link/ether ([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})', result.stdout)
            if mac_match:
                current_mac = mac_match.group(1)
                # Change only the last character (safest option)
                # Keep first 5 parts, change only the last part
                parts = current_mac.split(':')
                # Change only the last 2 characters (last byte)
                parts[5] = '%02x' % random.randint(0, 255)
                return ':'.join(parts)
    except:
        pass
    
    # Fallback: generate completely random MAC
    return ':'.join(['%02x' % random.randint(0, 255) for _ in range(6)])

def change_mac_address():
    """Change MAC address of the network interface"""
    interface = get_network_interface()
    new_mac = generate_random_mac()
    
    try:
        print(f"Attempting to change MAC address for interface: {interface}")
        
        # Check if interface exists
        result = subprocess.run(['ip', 'link', 'show', interface], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Interface {interface} not found. Available interfaces:")
            subprocess.run(['ip', 'link', 'show'], check=False)
            return False
        
        # Bring interface down
        print(f"Bringing {interface} down...")
        result = subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', interface, 'down'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to bring interface down: {result.stderr}")
            return False
        
        # Change MAC address
        print(f"Changing MAC address to: {new_mac}")
        result = subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', interface, 'address', new_mac], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to change MAC address: {result.stderr}")
            # Try to bring interface back up
            subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', interface, 'up'], 
                          capture_output=True)
            return False
        
        # Bring interface up
        print(f"Bringing {interface} up...")
        result = subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', interface, 'up'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to bring interface up: {result.stderr}")
            return False
        
        # Verify MAC address change
        time.sleep(1)
        result = subprocess.run(['ip', 'link', 'show', interface], 
                              capture_output=True, text=True)
        if new_mac in result.stdout:
            print(f"MAC address successfully changed to: {new_mac}")
            return True
        else:
            print(f"MAC address change verification failed")
            return False
        
    except Exception as e:
        print(f"Unexpected error changing MAC address: {e}")
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
        mac_success = change_mac_address()
        if not mac_success:
            print(f"Request {i+1}: MAC change failed, skipping...")
            continue
        
        # Wait longer for network to stabilize and get new IP
        print(f"Request {i+1}: Waiting for network to stabilize...")
        time.sleep(5)  # Increased wait time
        
        # Check network connectivity
        try:
            test_response = requests.get('https://www.google.com', timeout=5)
            print(f"Request {i+1}: Network connectivity OK")
        except:
            print(f"Request {i+1}: Network connectivity failed, retrying...")
            time.sleep(10)
        
        while True:
            retry_count += 1
            
            try:
                response = requests.post(GRAPHQL_URL, headers=headers, json=BODY, verify=False, timeout=10)
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
                        
            except requests.exceptions.ConnectionError as e:
                print(f"Request {i+1}: CONNECTION ERROR - {str(e)}")
                print(f"Request {i+1}: Waiting 10 seconds before retry...")
                time.sleep(10)
            except requests.exceptions.Timeout as e:
                print(f"Request {i+1}: TIMEOUT ERROR - {str(e)}")
                print(f"Request {i+1}: Waiting 5 seconds before retry...")
                time.sleep(5)
            except Exception as e:
                print(f"Request {i+1}: ERROR - {str(e)}")
                print(f"Request {i+1}: Waiting 5 seconds before retry...")
                time.sleep(5)
    
    print(f"\n=== Results ===")
    print(f"Total requests: {num_requests} | Success: {success_count} | Failed: {num_requests - success_count}")
    print(f"Success rate: {(success_count/num_requests)*100:.1f}%")

if __name__ == "__main__":
    test_requests_with_headers(num_requests=100000)
