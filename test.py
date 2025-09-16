import requests
import time
import json
import logging
import csv
import sys
import argparse
from graphql_queries import create_graphql_body, GRAPHQL_URL, GRAPHQL_HEADERS

# 기본 설정
BOUNDS_OFFSET = 0.004            # 검색 범위 (약 0.4km)
SEARCH_QUERY = "음식점"
START_INDEX = 1
DISPLAY_COUNT = 100

# 그리드 파일 경로
GRID_CSV_PATH = "spot.csv"

# 로그 파일 설정
RESTAURANTS_LOG_FILE = "log_restaurants.log"
EXCEPT_SPOTS_LOG_FILE = "log_exceptSpot.log"

# 재시도 딜레이 시간
RETRY_DELAY = 1

# API 요청 간 딜레이 시간 (초)
REQUEST_DELAY = 5
# REQUEST_DELAY = 0

# API 요청 카운터 및 딜레이 설정
REQUEST_COUNTER = 0
DELAY_EVERY_N_REQUESTS = 150
DELAY_SECONDS = 0

# 토글 설정 (True: 마지막 그리드 다음부터 시작, False: 처음부터 시작)
START_FROM_LAST_GRID = True

# 실행 모드 설정 (명령행 인수로 받음)
# 0: index % 6 == 0인 행들만 처리 (0, 6, 12, 18, ...)
# 1: index % 6 == 1인 행들만 처리 (1, 7, 13, 19, ...)
# 2: index % 6 == 2인 행들만 처리 (2, 8, 14, 20, ...)
# 3: index % 6 == 3인 행들만 처리 (3, 9, 15, 21, ...)
# 4: index % 6 == 4인 행들만 처리 (4, 10, 16, 22, ...)
# 5: index % 6 == 5인 행들만 처리 (5, 11, 17, 23, ...)

def create_variables(latitude, longitude, start_index):
    """GraphQL 요청에 사용할 variables 생성"""
    # 공통 데이터 계산
    x_str = str(longitude)
    y_str = str(latitude)
    # 서남동북
    bounds = f"{longitude - BOUNDS_OFFSET};{latitude - BOUNDS_OFFSET};{longitude + BOUNDS_OFFSET};{latitude + BOUNDS_OFFSET}"
    
    return {
        "isNmap": True,
        "restaurantListInput": {
            "query": SEARCH_QUERY,
            "x": x_str,
            "y": y_str,
            "start": start_index,
            "display": DISPLAY_COUNT,
            "takeout": None,
            "orderBenefit": None,
            "isCurrentLocationSearch": True,
            "filterOpening": None,
            "deviceType": "pcmap",
            "bounds": bounds,
            "isPcmap": True
        },
        "restaurantListFilterInput": {
            "x": x_str,
            "y": y_str,
            "display": DISPLAY_COUNT,
            "start": start_index,
            "query": SEARCH_QUERY,
            "bounds": bounds,
            "isCurrentLocationSearch": True
        },
    }

def check_and_delay_request():
    """API 요청 카운터를 증가시키고 100번마다 30초 딜레이"""
    global REQUEST_COUNTER
    REQUEST_COUNTER += 1
    
    if REQUEST_COUNTER % DELAY_EVERY_N_REQUESTS == 0:
        print(f"⏸️ {REQUEST_COUNTER}번째 요청 완료. {DELAY_SECONDS}초 대기 중...")
        time.sleep(DELAY_SECONDS)
        print(f"▶️ {DELAY_SECONDS}초 대기 완료. 계속 진행합니다.")

def fetch_restaurants_page(latitude, longitude, start_index):
    """하나의 페이지 데이터를 가져오는 함수"""
    # API 요청 전 딜레이 체크
    check_and_delay_request()
    
    variables = create_variables(latitude, longitude, start_index)
    body = [create_graphql_body(variables)]
    
    response = requests.post(GRAPHQL_URL, headers=GRAPHQL_HEADERS, json=body, timeout=30)
    
    if response.status_code != 200:
        return None, f"HTTP 에러 {response.status_code}"
    
    data = response.json()
    if isinstance(data, list) and len(data) > 0:
        data = data[0]
    
    if 'data' not in data or 'restaurants' not in data['data']:
        return None, "데이터 구조 오류"
    
    restaurant_data = data['data']['restaurants']
    
    # API 요청 간 딜레이
    time.sleep(REQUEST_DELAY)
    
    return restaurant_data, None

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.FileHandler(RESTAURANTS_LOG_FILE, encoding='utf-8-sig')
        ]
    )

def log_except_spot(grid_id, latitude, longitude):
    """0개 음식점이 발견된 좌표를 log_exceptSpot.log에 저장"""
    with open(EXCEPT_SPOTS_LOG_FILE, 'a', encoding='utf-8-sig') as f:
        f.write(f"{grid_id},{latitude},{longitude}\n")

def log_header():
    """CSV 헤더를 한 번만 출력"""
    header = "grid_id,center_lat,center_lon,id,x,y,businessCategory,category,phone,detailCid,markerId,fullAddress,categoryCodeList,visitorReviewCount,visitorReviewScore,blogCafeReviewCount,totalReviewCount,name"
    logging.info(header)

def log_restaurant_data(restaurants, grid_id, latitude, longitude):
    """음식점 데이터를 로그 파일에 저장"""
    if not restaurants:
        logging.error(f"그리드 {grid_id}에 저장할 데이터 없음")
        return
    
    for restaurant in restaurants:
        # detailCid 전체 딕셔너리를 문자열로 변환 (모든 정보 보존)
        detail_cid = restaurant.get('detailCid', {})
        if isinstance(detail_cid, dict):
            detail_cid_value = str(detail_cid)
        else:
            detail_cid_value = str(detail_cid)
        
        # 한 줄로 모든 정보를 저장 (그리드 정보 포함)
        row_data = (
            f"{grid_id},"
            f"{latitude},"
            f"{longitude},"
            f"{restaurant.get('id', 'N/A')},"
            f"{restaurant.get('x', 'N/A')},"
            f"{restaurant.get('y', 'N/A')},"
            f"{restaurant.get('businessCategory', 'N/A')},"
            f'"{restaurant.get("category", "N/A")}",'
            f'"{restaurant.get("phone", "N/A")}",'
            f'"{detail_cid_value}",'
            f"{restaurant.get('markerId', 'N/A')},"
            f'"{restaurant.get("fullAddress", "N/A")}",'
            f'"{restaurant.get("categoryCodeList", "N/A")}",'
            f'"{restaurant.get("visitorReviewCount", "N/A")}",'
            f'"{restaurant.get("visitorReviewScore", "N/A")}",'
            f'"{restaurant.get("blogCafeReviewCount", "N/A")}",'
            f'"{restaurant.get("totalReviewCount", "N/A")}",'
            f'"{restaurant.get("name", "이름없음")}"'
        )
        logging.info(row_data)

def save_results(restaurants, count, grid_id):
    """결과를 JSON 파일로 저장"""
    if restaurants:
        filename = f"restaurants_grid_{grid_id}.json"
        with open(filename, 'w', encoding='utf-8-sig') as f:
            json.dump(restaurants, f, indent=2, ensure_ascii=False)
        print(f"📁 그리드 {grid_id}: JSON 저장 완료")
    else:
        print(f"❌ 그리드 {grid_id}: 저장할 데이터 없음")

def collect_restaurants_from_grid(latitude, longitude, grid_id, progress_prefix):
    """하나의 그리드에서 음식점 데이터 수집"""
    print(f"{progress_prefix} 🔍 그리드 {grid_id}: {SEARCH_QUERY} 검색 시작 (위도:{latitude}, 경도:{longitude})")
    
    all_restaurants = []
    current_start = START_INDEX
    page_count = 0
    total_from_api = None
    
    while True:
        page_count += 1
        
        try:
            restaurant_data, error = fetch_restaurants_page(latitude, longitude, current_start)
            
            if error:
                print(f"{progress_prefix} ❌ 그리드 {grid_id} {page_count}페이지: {error}")
                return None, error
            
            items = restaurant_data.get('items', [])
            
            # 첫 페이지에서 총 개수 확인
            if page_count == 1:
                total_from_api = restaurant_data.get('total', 0)
                print(f"{progress_prefix} 📊 그리드 {grid_id}: 총 {total_from_api}개 음식점 발견")
                
                # 0개 음식점인 경우 exceptSpot.log에 저장
                if total_from_api == 0:
                    log_except_spot(grid_id, latitude, longitude)
                    print(f"{progress_prefix} ⚠️ 그리드 {grid_id}: 0개 음식점 - exceptSpot.log에 저장")
                    return [], None  # 빈 리스트와 None 에러 반환
            
            # 아이템이 없으면 종료
            if not items:
                break
            
            print(f"{progress_prefix} 📄 그리드 {grid_id} {page_count}페이지: {len(items)}개 (진행률: {len(all_restaurants)}/{total_from_api})")
            
            # 데이터 수집
            all_restaurants.extend(items)
            
            # 현재까지 수집된 데이터가 100개 미만이면 다음 페이지 스캔 중단
            if len(all_restaurants) < 100:
                print(f"{progress_prefix} ⚡ 그리드 {grid_id}: 현재까지 {len(all_restaurants)}개 (100개 미만) - 다음 페이지 스캔 중단")
                break
            
            current_start += DISPLAY_COUNT
            
            # # API 부하 방지
            # time.sleep(0.3)
            
        except Exception as e:
            error_msg = f"{progress_prefix} ❌ 그리드 {grid_id} {page_count}페이지 오류: {e}"
            print(f"{progress_prefix} {error_msg}")
            return None, error_msg
    
    print(f"{progress_prefix} ✅ 그리드 {grid_id}: {len(all_restaurants)}개 음식점 수집 완료")
    return all_restaurants, None

def read_except_spots():
    """log_exceptSpot.log에서 제외할 그리드 ID들을 읽기"""
    except_spots = set()
    try:
        with open(EXCEPT_SPOTS_LOG_FILE, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(',')
                    if len(parts) >= 1:
                        # BOM 문자 제거 및 숫자만 추출
                        grid_id = parts[0].strip().replace('\ufeff', '')
                        if grid_id.isdigit():
                            except_spots.add(grid_id)
        print(f"📋 제외할 그리드 {len(except_spots)}개 발견")
    except FileNotFoundError:
        print(f"📋 {EXCEPT_SPOTS_LOG_FILE} 파일이 없습니다. 모든 그리드를 처리합니다.")
    return except_spots

def read_processed_grids():
    """log_restaurants.log에서 이미 처리된 그리드 ID들을 읽기"""
    processed_grids = set()
    try:
        with open(RESTAURANTS_LOG_FILE, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line and ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 1:
                        # 첫 번째 컬럼이 grid_id
                        grid_id = parts[0].strip().replace('\ufeff', '')
                        if grid_id.isdigit():
                            processed_grids.add(grid_id)
        print(f"📋 이미 처리된 그리드 {len(processed_grids)}개 발견")
    except FileNotFoundError:
        print(f"📋 {RESTAURANTS_LOG_FILE} 파일이 없습니다. 처음부터 시작합니다.")
    return processed_grids

def main():
    """메인 실행 함수"""
    global REQUEST_COUNTER
    
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description='음식점 데이터 수집 프로그램')
    parser.add_argument('--mode', type=int, required=True, choices=[0,1,2,3,4,5], 
                       help='실행 모드 (0-5): index %% 6 == mode인 행들만 처리')
    args = parser.parse_args()
    
    EXECUTION_MODE = args.mode
    print(f"🚀 실행 모드: {EXECUTION_MODE} (index % 6 == {EXECUTION_MODE}인 행들 처리)")
    
    # 로깅 설정
    setup_logging()
    
    # 제외할 그리드 ID들 읽기
    except_spots = read_except_spots()
    processed_grids = read_processed_grids()
    
    # 마지막 처리된 그리드 ID 다음부터 시작하기 위한 시작 그리드 ID 찾기
    start_grid_id = 1
    if START_FROM_LAST_GRID and processed_grids:
        # processed_grids에서 가장 큰 그리드 ID 찾기
        max_grid_id = max(int(grid_id) for grid_id in processed_grids)
        start_grid_id = max_grid_id + 1
        print(f"🚀 마지막 처리된 그리드 ID: {max_grid_id}, 다음 그리드부터 시작: {start_grid_id}")
    else:
        print(f"🚀 처음부터 시작합니다. (START_FROM_LAST_GRID: {START_FROM_LAST_GRID})")
    
    # 헤더를 한 번만 출력
    log_header()
    
    print("🚀 그리드별 음식점 수집 시작")
    print(f"📊 {DELAY_EVERY_N_REQUESTS}번마다 {DELAY_SECONDS}초 대기 설정")
    print(f"📊 매 요청마다 {REQUEST_DELAY}초 대기 설정")
    
    try:
        # CSV 파일 읽기
        with open(GRID_CSV_PATH, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            grid_data = list(reader)
        
        print(f"📊 총 {len(grid_data)}개 그리드 발견")
        
        # ===== 1단계: 이미 처리된 그리드들을 필터링해서 제거 =====
        # - except_spots에 있는 그리드 ID들 제외
        # - start_grid_id보다 작은 그리드 ID들 제외
        filtered_grid_data = []
        for index, grid in enumerate(grid_data):
            grid_id = grid['grid_id']
            
            # 실행 모드에 맞는 행만 처리 (index % 6 == EXECUTION_MODE)
            if index % 6 != EXECUTION_MODE:
                continue
                
            # except_spots가 비어있지 않을 때만 체크
            if except_spots and grid_id in except_spots:
                continue
            # 이미 처리된 그리드는 제외
            if processed_grids and grid_id in processed_grids:
                continue
            # start_grid_id보다 크거나 같은 그리드만 포함
            if int(grid_id) >= start_grid_id:
                filtered_grid_data.append(grid)
        print(f"🔍 모드 {EXECUTION_MODE} 처리할 그리드 {len(filtered_grid_data)}개 (제외: {len(except_spots)}개, 처리완료: {len(processed_grids)}개, 시작 그리드: {start_grid_id})")
        
        # ===== 2단계: 필터링된 그리드들만 처리 =====
        for grid_info in filtered_grid_data:
            grid_id = grid_info['grid_id']
            latitude = float(grid_info['latitude'])
            longitude = float(grid_info['longitude'])
            
            # 진행률 표시 (필터링된 데이터 기준)
            current_index = len([g for g in filtered_grid_data if int(g['grid_id']) < int(grid_id)]) + 1
            progress = f"[{current_index}/{len(filtered_grid_data)}]"
            
            # 재시도 로직 (무한 반복)
            retry_count = 0
            success = False
            
            while not success:
                try:
                    if retry_count > 0:
                        print(f"🔄 그리드 {grid_id} 재시도 {retry_count}회")
                    
                    # 그리드에서 음식점 수집
                    restaurants, error = collect_restaurants_from_grid(latitude, longitude, grid_id, progress)
                    
                    if error:
                        print(f"❌ 그리드 {grid_id} 수집 실패: {error}")
                        print(f"🔄 {RETRY_DELAY}초 후 재시도...")
                        time.sleep(RETRY_DELAY)
                        retry_count += 1
                        continue
                    
                    # 0개 음식점인 경우도 성공으로 처리 (log_exceptSpot.log에 이미 저장됨)
                    if restaurants is not None:  # None이 아닌 경우 (빈 리스트도 포함)
                        if len(restaurants) > 0:
                            # 로그 파일에 데이터 저장 (헤더 없이)
                            log_restaurant_data(restaurants, grid_id, latitude, longitude)
                        
                        print(f"✅ 그리드 {grid_id} 완료 (총 요청 수: {REQUEST_COUNTER})")
                        print()
                        success = True
                    
                except Exception as e:
                    print(f"❌ 그리드 {grid_id} 처리 중 예외 발생: {e}")
                    print(f"🔄 {RETRY_DELAY}초 후 재시도...")
                    time.sleep(RETRY_DELAY)
                    retry_count += 1
        
        print("🎉 모든 그리드 수집 완료!")
        print(f"📊 총 API 요청 수: {REQUEST_COUNTER}회")
        
    except FileNotFoundError:
        print(f"❌ {GRID_CSV_PATH} 파일을 찾을 수 없습니다.")
        return
    except Exception as e:
        print(f"❌ 프로그램 실행 중 예외 발생: {e}")
        return

if __name__ == "__main__":
    main()