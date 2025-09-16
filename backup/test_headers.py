#!/usr/bin/env python3
"""
헤더 테스트 스크립트
Playwright를 사용한 동적 헤더 생성이 정상적으로 작동하는지 테스트합니다.
"""

from graphql_queries import get_graphql_headers, refresh_headers_and_cookies
import requests
import json

def test_headers():
    """헤더 생성 및 API 요청 테스트"""
    print("=== 헤더 테스트 시작 ===")
    
    # 1. 헤더와 쿠키 가져오기
    print("1. 헤더와 쿠키 가져오기...")
    headers, cookies = get_graphql_headers()
    print(f"헤더: {headers}")
    print(f"쿠키 개수: {len(cookies)}")
    
    # 2. 간단한 GraphQL 요청 테스트
    print("\n2. GraphQL API 요청 테스트...")
    
    # 테스트용 간단한 쿼리
    test_query = {
        "operationName": "getRestaurants",
        "variables": {
            "restaurantListInput": {
                "query": "서울",
                "x": "126.9780",
                "y": "37.5665",
                "start": 1,
                "display": 10,
                "isCurrentLocationSearch": True,
                "deviceType": "pcmap",
                "bounds": "126.9740;37.5625;126.9820;37.5705",
                "isPcmap": True
            },
            "restaurantListFilterInput": {
                "x": "126.9780",
                "y": "37.5665",
                "display": 10,
                "start": 1,
                "query": "서울",
                "bounds": "126.9740;37.5625;126.9820;37.5705",
                "isCurrentLocationSearch": True
            }
        },
        "query": "query getRestaurants($restaurantListInput: RestaurantListInput, $restaurantListFilterInput: RestaurantListFilterInput) { restaurants: restaurantList(input: $restaurantListInput) { items { id name x y __typename } total __typename } }"
    }
    
    try:
        with requests.Session() as session:
            for name, value in cookies.items():
                session.cookies.set(name, value)
            
            response = session.post(
                "https://pcmap-api.place.naver.com/graphql",
                headers=headers,
                json=[test_query],
                timeout=10
            )
            
            print(f"응답 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                
                if 'data' in data and 'restaurants' in data['data']:
                    restaurants = data['data']['restaurants']['items']
                    print(f"✅ 성공! {len(restaurants)}개 음식점 데이터 수신")
                    if restaurants:
                        print(f"첫 번째 음식점: {restaurants[0].get('name', 'N/A')}")
                else:
                    print("❌ 데이터 구조 오류")
                    print(f"응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"❌ HTTP 에러: {response.status_code}")
                print(f"응답 내용: {response.text[:200]}...")
                
    except Exception as e:
        print(f"❌ 요청 중 예외 발생: {e}")
    
    # 3. 헤더 새로고침 테스트
    print("\n3. 헤더 새로고침 테스트...")
    refresh_headers_and_cookies()
    print("✅ 헤더 새로고침 완료")
    
    print("\n=== 헤더 테스트 완료 ===")

if __name__ == "__main__":
    test_headers()
