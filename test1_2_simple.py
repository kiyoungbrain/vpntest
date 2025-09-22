import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """간단한 테스트 버전"""
    logger.info("=== 간단한 테스트 시작 ===")
    
    try:
        # 1. 데이터베이스 연결
        conn = psycopg2.connect(
            host='kypostgresql.sldb.iwinv.net',
            port=5432,
            user='postgres',
            password='wjsfir1234!@',
            database='postgres'
        )
        logger.info("데이터베이스 연결 성공")
        
        # 2. 테이블 생성
        with conn.cursor() as cursor:
            cursor.execute("""
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
            """)
            conn.commit()
            logger.info("테이블 생성/확인 완료")
        
        # 3. 로그 파일 읽기 (작은 샘플만)
        df = pd.read_csv('log_restaurants.log', encoding='utf-8-sig', nrows=10)
        logger.info(f"로그 파일 읽기 완료: {len(df)}개 행 (샘플)")
        
        # 4. 간단한 데이터 삽입 테스트
        today = '2025-09-19'
        
        with conn.cursor() as cursor:
            # 첫 번째 행만 테스트
            if len(df) > 0:
                row = df.iloc[0]
                cursor.execute("""
                    INSERT INTO navermap_temp (
                        date, grid_id, center_lat, center_lon, restaurant_id, x, y,
                        business_category, category, phone, detail_cid, marker_id,
                        full_address, category_code_list, visitor_review_count,
                        visitor_review_score, blog_cafe_review_count, total_review_count, name
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    today,
                    row.get('grid_id'),
                    row.get('center_lat'),
                    row.get('center_lon'),
                    row.get('id'),
                    row.get('x'),
                    row.get('y'),
                    row.get('businessCategory'),
                    row.get('category'),
                    row.get('phone'),
                    str(row.get('detailCid')),
                    row.get('markerId'),
                    row.get('fullAddress'),
                    str(row.get('categoryCodeList')),
                    row.get('visitorReviewCount'),
                    row.get('visitorReviewScore'),
                    row.get('blogCafeReviewCount'),
                    row.get('totalReviewCount'),
                    row.get('name')
                ))
                conn.commit()
                logger.info("테스트 데이터 삽입 완료")
        
        logger.info("=== 테스트 완료 ===")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("데이터베이스 연결 종료")

if __name__ == "__main__":
    main()
