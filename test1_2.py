import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Dict, Any
import sys
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def read_config():
    """config 파일에서 데이터베이스 연결 정보 읽기"""
    config = {}
    try:
        with open('backup/config', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 빈 줄과 주석 줄을 제외하고 실제 데이터만 추출
            data_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    data_lines.append(line)
            
            # 데이터베이스 정보는 처음 4줄
            if len(data_lines) >= 4:
                config['host'] = data_lines[0]
                config['port'] = int(data_lines[1])
                config['user'] = data_lines[2]
                config['password'] = data_lines[3]
                config['database'] = 'postgres'  # 기본 데이터베이스
            else:
                raise ValueError("Config 파일에 충분한 데이터가 없습니다.")
        return config
    except Exception as e:
        logger.error(f"Config 파일 읽기 실패: {e}")
        return None

def connect_to_database(config):
    """데이터베이스에 연결"""
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        logger.info("데이터베이스 연결 성공")
        return conn
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        return None

def create_table(conn):
    """navermap_temp 테이블 생성"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS navermap_temp (
        date DATE,
        id SERIAL PRIMARY KEY,
        grid_id INTEGER,
        center_lat DECIMAL(10, 8),
        center_lon DECIMAL(11, 8),
        restaurant_id BIGINT,
        x DECIMAL(11, 8),
        y DECIMAL(10, 8),
        business_category VARCHAR(100),
        category VARCHAR(200),
        phone VARCHAR(50),
        detail_cid TEXT,
        marker_id BIGINT,
        full_address TEXT,
        category_code_list TEXT,
        visitor_review_count VARCHAR(20),
        visitor_review_score VARCHAR(10),
        blog_cafe_review_count VARCHAR(20),
        total_review_count VARCHAR(20),
        name VARCHAR(200),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(create_table_sql)
            conn.commit()
            logger.info("navermap_temp 테이블 생성/확인 완료")
    except Exception as e:
        logger.error(f"테이블 생성 실패: {e}")
        raise

def read_log_file(file_path):
    """로그 파일을 읽어서 DataFrame으로 변환"""
    try:
        # CSV 파일로 읽기 (헤더가 있으므로)
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        logger.info(f"로그 파일 읽기 완료: {len(df)}개 행")
        return df
    except Exception as e:
        logger.error(f"로그 파일 읽기 실패: {e}")
        return None

def remove_duplicates(df):
    """중복 제거 - restaurant_id를 기준으로 중복 제거"""
    if df is None or df.empty:
        return df
    
    # restaurant_id가 있는 행만 필터링 (더 엄격한 필터링)
    df_filtered = df[
        (df['id'].notna()) & 
        (df['id'] != 'N/A') & 
        (df['id'] != 'None') & 
        (df['id'] != '') &
        (df['id'].astype(str).str.strip() != '')
    ].copy()
    
    # id 컬럼을 문자열로 변환하고 공백 제거
    df_filtered['id'] = df_filtered['id'].astype(str).str.strip()
    
    # 중복 제거 전후 개수 확인
    before_count = len(df_filtered)
    
    # restaurant_id를 기준으로 중복 제거 (첫 번째 값만 유지)
    df_deduplicated = df_filtered.drop_duplicates(subset=['id'], keep='first')
    
    after_count = len(df_deduplicated)
    removed_count = before_count - after_count
    
    logger.info(f"중복 제거 완료: {len(df)} -> {len(df_deduplicated)}개 행 (제거된 중복: {removed_count}개)")
    
    # 중복된 ID들 확인 (디버깅용)
    if removed_count > 0:
        duplicated_ids = df_filtered[df_filtered.duplicated(subset=['id'], keep=False)]['id'].unique()
        logger.info(f"중복된 restaurant_id들: {duplicated_ids[:10]}...")  # 처음 10개만 표시
    
    return df_deduplicated

def clean_data(df):
    """데이터 정리 및 타입 변환"""
    if df is None or df.empty:
        return df
    
    # 문자열 데이터 정리
    string_columns = ['category', 'phone', 'fullAddress', 'categoryCodeList', 
                     'visitorReviewCount', 'visitorReviewScore', 'blogCafeReviewCount', 
                     'totalReviewCount', 'name']
    
    for col in string_columns:
        if col in df.columns:
            # 따옴표 제거 및 None 값 처리
            df[col] = df[col].astype(str).str.replace('"', '').str.replace("'", "")
            df[col] = df[col].replace('N/A', None)
            df[col] = df[col].replace('None', None)
    
    # 숫자 데이터 정리
    numeric_columns = ['grid_id', 'center_lat', 'center_lon', 'id', 'x', 'y', 'markerId']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

def insert_data_to_db(conn, df):
    """데이터베이스에 데이터 삽입"""
    if df is None or df.empty:
        logger.warning("삽입할 데이터가 없습니다.")
        return
    
    # 오늘 날짜 가져오기
    today = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"데이터 삽입 날짜: {today}")
    
    # 컬럼명을 데이터베이스 스키마에 맞게 매핑
    column_mapping = {
        'grid_id': 'grid_id',
        'center_lat': 'center_lat',
        'center_lon': 'center_lon',
        'id': 'restaurant_id',
        'x': 'x',
        'y': 'y',
        'businessCategory': 'business_category',
        'category': 'category',
        'phone': 'phone',
        'detailCid': 'detail_cid',
        'markerId': 'marker_id',
        'fullAddress': 'full_address',
        'categoryCodeList': 'category_code_list',
        'visitorReviewCount': 'visitor_review_count',
        'visitorReviewScore': 'visitor_review_score',
        'blogCafeReviewCount': 'blog_cafe_review_count',
        'totalReviewCount': 'total_review_count',
        'name': 'name'
    }
    
    # 컬럼명 변경
    df_mapped = df.rename(columns=column_mapping)
    
    # 필요한 컬럼만 선택
    required_columns = list(column_mapping.values())
    df_final = df_mapped[required_columns]
    
    # 데이터 삽입 (date 컬럼을 맨 앞에 추가)
    insert_sql = """
    INSERT INTO navermap_temp (
        date, grid_id, center_lat, center_lon, restaurant_id, x, y,
        business_category, category, phone, detail_cid, marker_id,
        full_address, category_code_list, visitor_review_count,
        visitor_review_score, blog_cafe_review_count, total_review_count, name
    ) VALUES %s
    """
    
    try:
        with conn.cursor() as cursor:
            # 각 행에 오늘 날짜를 맨 앞에 추가
            data_tuples = []
            for row in df_final.values:
                row_with_date = (today,) + tuple(row)
                data_tuples.append(row_with_date)
            
            # 배치 삽입
            execute_values(
                cursor, insert_sql, data_tuples,
                template=None, page_size=1000
            )
            conn.commit()
            logger.info(f"데이터 삽입 완료: {len(data_tuples)}개 행 (날짜: {today})")
            
    except Exception as e:
        logger.error(f"데이터 삽입 실패: {e}")
        conn.rollback()
        raise

def main():
    """메인 실행 함수"""
    logger.info("=== 네이버맵 데이터 중복 제거 및 DB 삽입 시작 ===")
    
    # 1. Config 파일 읽기
    config = read_config()
    if not config:
        logger.error("Config 파일을 읽을 수 없습니다.")
        return
    
    # 2. 데이터베이스 연결
    conn = connect_to_database(config)
    if not conn:
        logger.error("데이터베이스에 연결할 수 없습니다.")
        return
    
    try:
        # 3. 테이블 생성
        create_table(conn)
        
        # 4. 로그 파일 읽기
        df = read_log_file('log_restaurants.log')
        if df is None:
            logger.error("로그 파일을 읽을 수 없습니다.")
            return
        
        # 5. 데이터 정리
        df_cleaned = clean_data(df)
        
        # 6. 중복 제거
        df_deduplicated = remove_duplicates(df_cleaned)
        
        # 7. 데이터베이스에 삽입
        insert_data_to_db(conn, df_deduplicated)
        
        logger.info("=== 모든 작업 완료 ===")
        
    except Exception as e:
        logger.error(f"작업 중 오류 발생: {e}")
    finally:
        conn.close()
        logger.info("데이터베이스 연결 종료")

if __name__ == "__main__":
    main()