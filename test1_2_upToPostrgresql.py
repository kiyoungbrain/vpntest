import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Dict, Any
import sys
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_config():
    """데이터베이스 연결 정보 반환"""
    return {
        'host': 'kypostgresql.sldb.iwinv.net',
        'port': 5432,
        'user': 'postgres',
        'password': 'wjsfir1234!@',
        'database': 'postgres'
    }

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
        # 먼저 파일 크기 확인
        import os
        file_size = os.path.getsize(file_path)
        logger.info(f"파일 크기: {file_size / 1024 / 1024:.2f} MB")
        
        # 파일이 작으면 한 번에 읽기 (중복제거를 위해)
        if file_size < 50 * 1024 * 1024:  # 50MB 미만
            logger.info("파일이 작아서 한 번에 읽기")
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            logger.info(f"로그 파일 읽기 완료: {len(df)}개 행")
            return df
        else:
            # 큰 파일의 경우 청크로 읽되, 중복제거를 위해 ID만 먼저 수집
            logger.info("큰 파일이므로 ID 기반 중복제거 방식 사용")
            return read_large_file_with_dedup(file_path)
            
    except Exception as e:
        logger.error(f"로그 파일 읽기 실패: {e}")
        return None

def safe_convert_to_numeric(value, default=None):
    """안전하게 숫자로 변환 (numpy 타입을 Python 기본 타입으로 변환)"""
    if pd.isna(value) or value is None:
        return default
    
    # numpy 타입을 Python 기본 타입으로 변환
    if isinstance(value, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(value)
    if isinstance(value, (np.floating, np.float64, np.float32, np.float16)):
        return float(value)
    
    if isinstance(value, (int, float)):
        return value
    
    if isinstance(value, str):
        # 컬럼명이 값으로 들어온 경우 필터링
        if value.strip() in ['grid_id', 'center_lat', 'center_lon', 'id', 'x', 'y', 'markerId', 
                            'restaurant_id', 'marker_id', 'businessCategory', 'category', 
                            'phone', 'detailCid', 'fullAddress', 'categoryCodeList',
                            'visitorReviewCount', 'visitorReviewScore', 'blogCafeReviewCount',
                            'totalReviewCount', 'name']:
            return default
        try:
            numeric_value = pd.to_numeric(value, errors='coerce')
            if pd.isna(numeric_value):
                return default
            # numpy 타입이면 Python 기본 타입으로 변환
            if isinstance(numeric_value, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                return int(numeric_value)
            if isinstance(numeric_value, (np.floating, np.float64, np.float32, np.float16)):
                return float(numeric_value)
            return numeric_value
        except:
            return default
    
    try:
        numeric_value = pd.to_numeric(value, errors='coerce')
        if pd.isna(numeric_value):
            return default
        # numpy 타입이면 Python 기본 타입으로 변환
        if isinstance(numeric_value, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(numeric_value)
        if isinstance(numeric_value, (np.floating, np.float64, np.float32, np.float16)):
            return float(numeric_value)
        return numeric_value
    except:
        return default

def safe_convert_to_string(value, default=None):
    """안전하게 문자열로 변환 (numpy 타입 처리)"""
    if pd.isna(value) or value is None:
        return default
    
    # numpy 타입을 먼저 Python 기본 타입으로 변환
    if isinstance(value, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        value = int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32, np.float16)):
        value = float(value)
    elif isinstance(value, np.ndarray):
        # numpy 배열인 경우 첫 번째 요소 사용
        if len(value) > 0:
            value = value[0]
        else:
            return default
    
    if isinstance(value, str):
        # 컬럼명이 값으로 들어온 경우 필터링
        if value.strip() in ['grid_id', 'center_lat', 'center_lon', 'id', 'x', 'y', 'markerId', 
                            'restaurant_id', 'marker_id', 'businessCategory', 'category', 
                            'phone', 'detailCid', 'fullAddress', 'categoryCodeList',
                            'visitorReviewCount', 'visitorReviewScore', 'blogCafeReviewCount',
                            'totalReviewCount', 'name']:
            return default
        return value
    
    return str(value) if value is not None else default

def ensure_python_types(data_tuple):
    """튜플의 모든 값을 Python 기본 타입으로 변환 (numpy 타입 제거)"""
    result = []
    for value in data_tuple:
        if pd.isna(value) or value is None:
            result.append(None)
        elif isinstance(value, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            result.append(int(value))
        elif isinstance(value, (np.floating, np.float64, np.float32, np.float16)):
            result.append(float(value))
        elif isinstance(value, np.ndarray):
            if len(value) > 0:
                result.append(ensure_python_types((value[0],))[0])
            else:
                result.append(None)
        else:
            result.append(value)
    return tuple(result)

def process_large_file_direct_to_db(file_path, conn, today):
    """큰 파일을 직접 데이터베이스에 삽입 (메모리 효율적)"""
    try:
        # 먼저 전체 파일 크기 확인
        import os
        file_size = os.path.getsize(file_path)
        chunk_size = 1000
        
        logger.info(f"파일 크기: {file_size / 1024 / 1024:.2f} MB")
        
        # 중복 제거를 위한 processed_ids set (전역적으로 유지)
        processed_ids = set()
        total_inserted = 0
        total_chunks_processed = 0
        skipped_rows = 0
        
        insert_sql = """
        INSERT INTO navermap_temp (
            date, grid_id, center_lat, center_lon, restaurant_id, x, y,
            business_category, category, phone, detail_cid, marker_id,
            full_address, category_code_list, visitor_review_count,
            visitor_review_score, blog_cafe_review_count, total_review_count, name
        ) VALUES %s
        """
        
        logger.info("파일을 한 번만 읽으면서 중복 제거 및 DB 삽입 시작")
        
        with conn.cursor() as cursor:
            try:
                for i, chunk in enumerate(pd.read_csv(file_path, encoding='utf-8-sig', chunksize=chunk_size,
                                                    on_bad_lines='skip')):
                    total_chunks_processed = i + 1
                    
                    # 헤더 행이 데이터로 들어오는 것을 방지 (첫 번째 청크에서만 체크)
                    if i == 0 and len(chunk) > 0:
                        # 첫 번째 행이 헤더인지 확인
                        first_row_id = str(chunk.iloc[0].get('id', '')).strip()
                        if first_row_id in ['id', 'grid_id', 'center_lat', 'center_lon', 'restaurant_id']:
                            logger.warning("헤더 행이 데이터로 감지됨. 첫 번째 행을 건너뜁니다.")
                            chunk = chunk.iloc[1:].copy()
                    
                    # 유효한 ID만 필터링
                    chunk_clean = chunk[
                        (chunk['id'].notna()) & 
                        (chunk['id'] != 'N/A') & 
                        (chunk['id'] != 'None') &
                        (chunk['id'] != '') &
                        (chunk['id'].astype(str).str.strip() != '')
                    ].copy()
                    
                    if len(chunk_clean) == 0:
                        continue
                    
                    chunk_clean['id'] = chunk_clean['id'].astype(str).str.strip()
                
                    # 아직 처리되지 않은 ID들만 선택 (메모리 효율적)
                    data_tuples = []
                    for _, row in chunk_clean.iterrows():
                        try:
                            row_id = str(row['id']).strip()
                            
                            # ID가 컬럼명인 경우 스킵
                            if row_id in ['id', 'grid_id', 'center_lat', 'center_lon', 'restaurant_id', 
                                         'markerId', 'marker_id', 'businessCategory', 'category',
                                         'phone', 'detailCid', 'fullAddress', 'categoryCodeList',
                                         'visitorReviewCount', 'visitorReviewScore', 'blogCafeReviewCount',
                                         'totalReviewCount', 'name']:
                                skipped_rows += 1
                                continue
                            
                            if row_id not in processed_ids:
                                processed_ids.add(row_id)
                                
                                # 타입 변환 및 검증을 포함한 튜플 생성
                                data_tuple = (
                                    today,
                                    safe_convert_to_numeric(row.get('grid_id')),
                                    safe_convert_to_numeric(row.get('center_lat')),
                                    safe_convert_to_numeric(row.get('center_lon')),
                                    safe_convert_to_numeric(row.get('id')),  # restaurant_id
                                    safe_convert_to_numeric(row.get('x')),
                                    safe_convert_to_numeric(row.get('y')),
                                    safe_convert_to_string(row.get('businessCategory')),
                                    safe_convert_to_string(row.get('category')),
                                    safe_convert_to_string(row.get('phone')),
                                    safe_convert_to_string(row.get('detailCid')),
                                    safe_convert_to_numeric(row.get('markerId')),
                                    safe_convert_to_string(row.get('fullAddress')),
                                    safe_convert_to_string(row.get('categoryCodeList')),
                                    safe_convert_to_string(row.get('visitorReviewCount')),
                                    safe_convert_to_string(row.get('visitorReviewScore')),
                                    safe_convert_to_string(row.get('blogCafeReviewCount')),
                                    safe_convert_to_string(row.get('totalReviewCount')),
                                    safe_convert_to_string(row.get('name'))
                                )
                                # numpy 타입을 Python 기본 타입으로 최종 변환
                                data_tuple = ensure_python_types(data_tuple)
                                data_tuples.append(data_tuple)
                        except Exception as row_error:
                            skipped_rows += 1
                            if skipped_rows % 100 == 0:
                                logger.warning(f"행 처리 중 오류 발생 (누적 {skipped_rows}개 건너뜀): {row_error}")
                            continue
                    
                    if data_tuples:
                        try:
                            # 배치 삽입
                            execute_values(cursor, insert_sql, data_tuples, page_size=50)
                            total_inserted += len(data_tuples)
                        except Exception as insert_error:
                            logger.warning(f"배치 삽입 중 오류 발생: {insert_error}")
                            # 개별 삽입으로 재시도
                            for data_tuple in data_tuples:
                                try:
                                    execute_values(cursor, insert_sql, [data_tuple], page_size=1)
                                    total_inserted += 1
                                except Exception as single_error:
                                    skipped_rows += 1
                                    if skipped_rows % 100 == 0:
                                        logger.warning(f"개별 행 삽입 실패 (누적 {skipped_rows}개 건너뜀): {single_error}")
                    
                    # 진행률 표시 (더 자주)
                    if i % 10 == 0:  # 10청크마다 진행률 표시
                        logger.info(f"처리 중... 청크 {i+1}, 총 삽입: {total_inserted}개 행, 고유 ID: {len(processed_ids)}개, 건너뜀: {skipped_rows}개")
                        
                        # 커밋도 더 자주
                        conn.commit()
                    
                    # 메모리 정리
                    if i % 100 == 0:
                        import gc
                        gc.collect()
                
                # 최종 커밋
                conn.commit()
                logger.info(f"최종 완료: 총 {total_inserted}개 행 삽입, 총 {total_chunks_processed}개 청크 처리됨, 고유 ID: {len(processed_ids)}개, 건너뜀: {skipped_rows}개")
                
            except Exception as e:
                logger.warning(f"데이터 처리 중 일부 오류 발생: {e}, 현재까지 {total_inserted}개 행 삽입됨")
                conn.commit()  # 현재까지의 데이터라도 커밋
        
        return total_inserted
        
    except Exception as e:
        logger.error(f"큰 파일 처리 실패: {e}")
        return 0

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

def insert_data_to_db(conn, df, today):
    """데이터베이스에 데이터 삽입"""
    if df is None or df.empty:
        logger.warning("삽입할 데이터가 없습니다.")
        return
    
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
            
            # 배치 삽입 (메모리 효율성을 위해 작은 배치 크기)
            execute_values(
                cursor, insert_sql, data_tuples,
                template=None, page_size=100
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
    
    try:
        # 1. 데이터베이스 연결 정보 가져오기
        logger.info("1단계: 데이터베이스 연결 정보 가져오기")
        config = get_database_config()
        
        # 2. 데이터베이스 연결
        logger.info("2단계: 데이터베이스 연결 시도")
        conn = connect_to_database(config)
        if not conn:
            logger.error("데이터베이스에 연결할 수 없습니다.")
            return
        
        # 3. 테이블 생성
        logger.info("3단계: 테이블 생성/확인")
        create_table(conn)
        
        # 4. 날짜 설정
        today = '2025-11-21'
        logger.info(f"사용할 날짜: {today}")
        
        # 5. 로그 파일 처리 (무조건 직접 DB 삽입)
        logger.info("5단계: 로그 파일 직접 DB 삽입 시작")
        total_inserted = process_large_file_direct_to_db('log_restaurants.log', conn, today)
        logger.info(f"총 {total_inserted}개 행이 데이터베이스에 삽입되었습니다.")
        
        logger.info("=== 모든 작업 완료 ===")
        
    except Exception as e:
        logger.error(f"작업 중 오류 발생: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("데이터베이스 연결 종료")

if __name__ == "__main__":
    main()