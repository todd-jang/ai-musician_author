# backend/app/services/onprem.py

import requests # 예시: 온프레미스 API와 통신 시 사용
import os # 예시: 온프레미스 파일 경로 접근 시 필요할 수 있음
# import pyodbc or other DB library # 예시: 온프레미스 DB 접근 시 필요

# 온프레미스 자원 접속 정보 (환경 변수나 설정을 통해 관리)
ONPREM_API_URL = os.getenv("ONPREM_API_URL", "http://onpremise-server/api/")
# ONPREM_DB_CONNECTION_STRING = os.getenv("ONPREM_DB_CONNECTION_STRING", "...")

class OnPremService:
    """
    온프레미스 환경의 서비스 및 자원과 연동하는 클래스 예시
    """
    def get_data_from_legacy_db(self, query: str):
        """
        온프레미스 레거시 데이터베이스에서 데이터를 조회합니다.
        (실제 DB 연동 코드로 대체 필요)
        """
        print(f"온프레미스 DB에서 데이터 조회 시도: {query[:50]}...")
        # 예시: pyodbc 등을 사용하여 DB 연결 및 쿼리 실행
        # try:
        #     conn = pyodbc.connect(ONPREM_DB_CONNECTION_STRING)
        #     cursor = conn.cursor()
        #     cursor.execute(query)
        #     results = cursor.fetchall()
        #     conn.close()
        #     print("온프레미스 DB 조회 성공 (예시)")
        #     return results
        # except Exception as e:
        #     print(f"온프레미스 DB 조회 오류 (예시): {e}")
        #     return None
        # TODO: 실제 온프레미스 DB 연동 코드 구현
        return [{"example": "data from onpremise DB", "query": query}] # Mock 데이터 반환

    def send_data_to_onprem_api(self, payload: dict):
        """
        온프레미스 환경의 특정 API로 데이터를 전송합니다.
        """
        print(f"온프레미스 API ({ONPREM_API_URL})로 데이터 전송 시도...")
        try:
            response = requests.post(f"{ONPREM_API_URL}/receive_data", json=payload)
            response.raise_for_status() # HTTP 오류 발생 시 예외 발생
            print(f"온프레미스 API 전송 성공 (예시): 응답 상태 {response.status_code}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"온프레미스 API 전송 오류 (예시): {e}")
            return None
        # TODO: 실제 온프레미스 API 연동 코드 구현

    def process_with_onprem_gpu(self, task_data: dict):
        """
        온프레미스 GPU 서버에서 AI 처리 작업을 실행하도록 요청합니다.
        (IPC, 메시지 큐, RPC 등 통신 방식에 따라 코드 달라짐)
        """
        print(f"온프레미스 GPU 처리 요청 시도 (예시): {task_data}")
        # 예시: 온프레미스에 대기하고 있는 워커에게 메시지를 보내거나 API 호출
        # TODO: 실제 온프레미스 워커 연동 코드 구현 (e.g., RabbitMQ publish, gRPC call)
        return {"status": "task_submitted_to_onprem", "task_id": "onprem-task-123"} # Mock 응답

# 서비스 인스턴스 생성 (싱글톤 패턴처럼 사용하거나 DI 컨테이너에 등록)
onprem_service = OnPremService()

# 사용 예시:
# results = onprem_service.get_data_from_legacy_db("SELECT * FROM users LIMIT 10")
# api_response = onprem_service.send_data_to_onprem_api({"status": "processed", "id": 123})
# gpu_task = onprem_service.process_with_onprem_gpu({"pdf_key": "s3://...", "analysis_type": "inference"})
