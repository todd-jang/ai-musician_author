# backend/app/services/db_service.py

import os
import json
# 필요한 DB 드라이버 임포트
import psycopg2 # PostgreSQL
# try:
#     import cx_Oracle # Oracle (설치 필요: pip install cx_oracle)
# except ImportError:
#     cx_Oracle = None
# TODO: 다른 DB 드라이버 임포트

from typing import Dict, Any, Optional

# 로깅 설정 임포트 및 사용 (아래 2번 항목에서 설명)
import logging
logger = logging.getLogger(__name__)

# --- 설정 로드 ---
# 환경 변수에서 DB 타입 및 연결 정보 로드
# .env 파일 예시:
# DB_TYPE=postgresql
# POSTGRES_DB=...
# POSTGRES_USER=...
# POSTGRES_PASSWORD=...
# POSTGRES_HOST=...
# POSTGRES_PORT=5432
# # 또는
# # DB_TYPE=multi # 또는 hybrid
# # PRIMARY_DB_TYPE=postgresql
# # PRIMARY_DB_CONFIG={"db": "...", ...} # JSON 문자열 또는 별도 설정 파일
# # SECONDARY_DB_TYPE=oracle
# # SECONDARY_DB_CONFIG={"user": "...", ...}
# # LOG_DB_TYPE=elasticsearch # 로그 저장소는 보통 DB_TYPE과는 다름
# # ELASTICSEARCH_HOST=...

# 여기서는 간단히 환경 변수에서 직접 설정 로드
PRIMARY_DB_TYPE = os.getenv("PRIMARY_DB_TYPE", "postgresql")
# PRIMARY_DB_CONFIG는 환경 변수에서 직접 로드하거나, 필요시 JSON 문자열 파싱 등 사용
# 예시: PG 연결 정보
PG_CONFIG = {
    "database": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT", "5432")
}
# 예시: Oracle 연결 정보
ORACLE_CONFIG = {
    "user": os.getenv("ORACLE_USER"),
    "password": os.getenv("ORACLE_PASSWORD"),
    "dsn": os.getenv("ORACLE_DSN")
}
# TODO: 다른 DB 연결 설정 로드

# --- 데이터베이스 연결 관리 ---
# 실제 애플리케이션에서는 커넥션 풀(Connection Pool)을 사용하는 것이 성능과 효율성 면에서 훨씬 좋습니다.
# 여기서는 개념적인 연결 함수만 제시합니다.

def get_db_connection(db_role: str = "primary"):
    """
    주어진 역할(role)에 맞는 데이터베이스 연결을 가져옵니다.
    role에 따라 PRIMARY_DB 또는 SECONDARY_DB 등으로 구분 가능.
    """
    # TODO: db_role에 따라 적절한 DB 타입과 설정을 선택하는 로직 구현
    # 현재는 PRIMARY_DB_TYPE에 따라 연결 시도
    db_type = PRIMARY_DB_TYPE
    config = PG_CONFIG if db_type == "postgresql" else ORACLE_CONFIG if db_type == "oracle" else None # 등등

    if not config:
         logger.error(f"Unsupported or unconfigured database role or type: {db_role}/{db_type}")
         return None

    try:
        if db_type == "postgresql":
            # psycopg2 연결
            # conn = psycopg2.connect(**config)
            # logger.info(f"Connected to PostgreSQL ({db_role} role).")
            # return conn
            # --- Mock 연결 ---
            logger.info(f"Mock PostgreSQL connection ({db_role} role).")
            class MockConnection:
                def cursor(self): return self
                def execute(self, query, params=None): logger.debug(f"Mock Execute: {query}, {params}"); pass
                def commit(self): logger.debug("Mock Commit"); pass
                def rollback(self): logger.debug("Mock Rollback"); pass
                def close(self): logger.debug("Mock Close"); pass
                def __enter__(self): return self
                def __exit__(self, exc_type, exc_val, exc_tb): self.close(); return False # Propagate exceptions
            return MockConnection()
            # --- Mock 연결 끝 ---


        elif db_type == "oracle":
            if cx_Oracle is None:
                 logger.error("cx_Oracle library not found. Cannot connect to Oracle DB.")
                 return None
            # TODO: cx_Oracle 연결
            # conn = cx_Oracle.connect(config["user"], config["password"], config["dsn"])
            # logger.info(f"Connected to Oracle DB ({db_role} role).")
            # return conn
            logger.info(f"Mock Oracle connection ({db_role} role).")
            return None # 실제 구현 필요

        # TODO: 다른 DB 타입 연결 로직 추가

        else:
            logger.error(f"Unknown database type '{db_type}' for role '{db_role}'.")
            return None

    except Exception as e:
        logger.error(f"Error connecting to database ({db_role} role, type: {db_type}): {e}", exc_info=True)
        return None

# --- DB Operation Functions ---
# 예시: save_task_result 함수 (위에서 정의한 스키마에 맞게 업데이트)

def save_task_result(result_payload: Dict[str, Any]) -> bool:
    """워커로부터 받은 최종 작업 결과를 데이터베이스에 저장합니다."""
    # 작업 정보는 Primary DB에 저장된다고 가정
    conn = get_db_connection("primary")
    if not conn:
        logger.error("데이터베이스 연결 실패. 작업 결과 저장 불가.")
        return False

    task_id = result_payload.get("task_id")
    if not task_id:
        logger.error("작업 결과 페이로드에 task_id가 없습니다.")
        return False

    try:
        # 트랜잭션 시작 (with conn 으로 자동 관리 가능)
        # with conn.cursor() as cur: # Mock 연결은 cursor() 메소드를 제공하도록 수정 필요
        cur = conn.cursor() # Mock 연결에서는 cur = conn; 으로 사용
        logger.info(f"작업 결과 저장 시작: {task_id}", extra={'extra_context': {'task_id': task_id}})

        # tasks 테이블 상태 업데이트
        cur.execute(
            """
            UPDATE tasks
            SET status = %s, completed_at = %s, error_message = %s
            WHERE task_id = %s
            """,
            (
                result_payload.get("status", "unknown"),
                result_payload.get("completed_at"),
                result_payload.get("error_details"),
                task_id
            )
        )
        logger.debug(f"tasks 테이블 업데이트 완료: {task_id}", extra={'extra_context': {'task_id': task_id}})


        # task_results 테이블에 결과 상세 삽입 또는 업데이트 (JSONB 사용)
        cur.execute(
            """
            INSERT INTO task_results (task_id, final_status, processing_time_seconds, detailed_results, completed_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (task_id) DO UPDATE
            SET final_status = EXCLUDED.final_status,
                processing_time_seconds = EXCLUDED.processing_time_seconds,
                detailed_results = EXCLUDED.detailed_results, -- JSONB 타입은 JSON 문자열 필요
                completed_at = EXCLUDED.completed_at;
            """,
            (
                task_id,
                result_payload.get("status", "unknown"),
                result_payload.get("processing_time_seconds"),
                json.dumps(result_payload.get("results_summary")), # 딕셔너리를 JSON 문자열로 직렬화
                result_payload.get("completed_at")
            )
        )
        logger.debug(f"task_results 테이블 삽입/업데이트 완료: {task_id}", extra={'extra_context': {'task_id': task_id}})


        conn.commit() # 변경사항 커밋
        logger.info(f"작업 결과 저장 성공: {task_id}", extra={'extra_context': {'task_id': task_id}})
        return True
    except Exception as e:
        conn.rollback() # 오류 발생 시 롤백
        logger.error(f"작업 결과 저장 중 오류 발생: {task_id}", extra={'extra_context': {'task_id': task_id, 'error': str(e)}}, exc_info=True)
        return False
    finally:
        # 연결 닫기
        if conn:
            conn.close()


# TODO: get_task_status_by_id, get_task_result_location, create_user 등 다른 DB 연동 함수 구현
# 이 함수들도 get_db_connection("primary") 등을 사용하여 필요한 DB 연결 획득
