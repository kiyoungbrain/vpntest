import pandas as pd
import psycopg2
from google.cloud import bigquery
from google.oauth2 import service_account
import logging
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
    """PostgreSQL 데이터베이스에 연결"""
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        
        # 임시 파일 크기 제한 해제
        with conn.cursor() as cursor:
            cursor.execute("SET temp_file_limit = -1")  # 무제한
            cursor.execute("SET work_mem = '256MB'")    # 작업 메모리 증가
            cursor.execute("SET maintenance_work_mem = '512MB'")  # 유지보수 작업 메모리 증가
        
        logger.info("PostgreSQL 데이터베이스 연결 성공 (임시 파일 제한 해제)")
        return conn
    except Exception as e:
        logger.error(f"PostgreSQL 데이터베이스 연결 실패: {e}")
        return None

def get_bigquery_client():
    """BigQuery 클라이언트 생성"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            'gcp_iam_svc_key_kiyoung.json'
        )
        client = bigquery.Client(
            credentials=credentials,
            project='vernal-dispatch-420407'
        )
        logger.info("BigQuery 클라이언트 생성 성공")
        return client
    except Exception as e:
        logger.error(f"BigQuery 클라이언트 생성 실패: {e}")
        return None

def create_bigquery_table(client):
    """BigQuery 테이블 생성"""
    try:
        dataset_id = 'platformData'
        table_id = 'naver'
        
        # 데이터셋 생성 (없으면)
        dataset_ref = client.dataset(dataset_id)
        try:
            client.get_dataset(dataset_ref)
            logger.info(f"데이터셋 {dataset_id} 이미 존재")
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            dataset = client.create_dataset(dataset, timeout=30)
            logger.info(f"데이터셋 {dataset_id} 생성 완료")
        
        # 테이블 스키마 정의
        schema = [
            bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("restaurant_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("x", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("y", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("business_category", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("category", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("phone", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("marker_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("full_address", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("category_code_list", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("visitor_review_count", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("visitor_review_score", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("blog_cafe_review_count", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("total_review_count", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("name", "STRING", mode="NULLABLE"),
        ]
        
        # 테이블 생성 (없으면)
        table_ref = dataset_ref.table(table_id)
        try:
            client.get_table(table_ref)
            logger.info(f"테이블 {table_id} 이미 존재")
        except Exception:
            table = bigquery.Table(table_ref, schema=schema)
            # date 컬럼으로 클러스터링 설정 (인덱싱 효과)
            table.clustering_fields = ["date"]
            table = client.create_table(table)
            logger.info(f"테이블 {table_id} 생성 완료 (date 클러스터링 적용)")
        
        return f"{dataset_id}.{table_id}"
        
    except Exception as e:
        logger.error(f"BigQuery 테이블 생성 실패: {e}")
        return None

def fetch_data_from_postgres(conn):
    """PostgreSQL에서 데이터 가져오기 (GROUP BY로 중복 제거)"""
    try:
        # 먼저 총 개수 확인 (PostgreSQL 호환 방식)
        count_query = "SELECT COUNT(*) FROM (SELECT DISTINCT date, restaurant_id FROM navermap_temp) as unique_combinations"
        with conn.cursor() as cursor:
            cursor.execute(count_query)
            total_count = cursor.fetchone()[0]
        
        logger.info(f"총 {total_count}개 고유 조합 발견")
        
        # GROUP BY로 중복 제거 (date, restaurant_id 기준)
        query = """
        SELECT 
            date,
            restaurant_id,
            MAX(x) as x,
            MAX(y) as y,
            MAX(business_category) as business_category,
            MAX(category) as category,
            MAX(phone) as phone,
            MAX(marker_id) as marker_id,
            MAX(full_address) as full_address,
            MAX(category_code_list) as category_code_list,
            MAX(visitor_review_count) as visitor_review_count,
            MAX(visitor_review_score) as visitor_review_score,
            MAX(blog_cafe_review_count) as blog_cafe_review_count,
            MAX(total_review_count) as total_review_count,
            MAX(name) as name
        FROM navermap_temp
        GROUP BY date, restaurant_id
        """
        
        with conn.cursor() as cursor:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            if rows:
                df = pd.DataFrame(rows, columns=columns)
                logger.info(f"PostgreSQL에서 {len(df)}개 행 가져오기 완료 (중복 제거됨)")
                return df
            else:
                logger.warning("가져올 데이터가 없습니다")
                return None
        
    except Exception as e:
        logger.error(f"PostgreSQL 데이터 가져오기 실패: {e}")
        return None

def upload_to_bigquery(client, table_id, df):
    """BigQuery에 데이터 업로드"""
    try:
        # 데이터 타입 변환
        df['date'] = pd.to_datetime(df['date']).dt.date
        df['x'] = pd.to_numeric(df['x'], errors='coerce')
        df['y'] = pd.to_numeric(df['y'], errors='coerce')
        df['marker_id'] = df['marker_id'].astype(str)
        
        # NaN 값을 None으로 변환
        df = df.where(pd.notnull(df), None)
        
        # BigQuery에 업로드
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",  # 기존 데이터 삭제 후 새로 삽입
            create_disposition="CREATE_IF_NEEDED"
        )
        
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  # 작업 완료 대기
        
        logger.info(f"BigQuery 업로드 완료: {len(df)}개 행")
        return True
        
    except Exception as e:
        logger.error(f"BigQuery 업로드 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    logger.info("=== PostgreSQL → BigQuery 데이터 이전 시작 ===")
    
    # 1. PostgreSQL 연결
    pg_config = get_database_config()
    pg_conn = connect_to_database(pg_config)
    if not pg_conn:
        logger.error("PostgreSQL 연결 실패")
        return
    
    # 2. BigQuery 클라이언트 생성
    bq_client = get_bigquery_client()
    if not bq_client:
        logger.error("BigQuery 클라이언트 생성 실패")
        pg_conn.close()
        return
    
    try:
        # 3. BigQuery 테이블 생성
        table_id = create_bigquery_table(bq_client)
        if not table_id:
            logger.error("BigQuery 테이블 생성 실패")
            return
        
        # 4. PostgreSQL에서 데이터 가져오기
        df = fetch_data_from_postgres(pg_conn)
        if df is None or df.empty:
            logger.error("가져올 데이터가 없습니다")
            return
        
        # 5. BigQuery에 업로드
        success = upload_to_bigquery(bq_client, table_id, df)
        if success:
            logger.info("=== 모든 작업 완료 ===")
        else:
            logger.error("=== 작업 실패 ===")
            
    except Exception as e:
        logger.error(f"작업 중 오류 발생: {e}")
    finally:
        pg_conn.close()
        logger.info("PostgreSQL 연결 종료")

if __name__ == "__main__":
    main()
