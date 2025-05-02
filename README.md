# backend/app/main.py

from fastapi import FastAPI

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI()

# 기본적인 라우트 정의 (선택 사항이지만 앱이 잘 작동하는지 확인하기 좋음)
@app.get("/")
def read_root():
    return {"message": "Personal Data Assistant Backend is running!"}

# 나중에 API 라우터를 포함시킬 부분
# from .api import api_router
# app.include_router(api_router)

# 이 파일을 직접 실행하려면:
# uvicorn app.main:app --reload
# (FastAPI 및 uvicorn 설치 필요: pip install fastapi uvicorn python-multipart boto3) 가상환경에서 backend/에서 pip install -r requirements.txt
웹 브라우저에서 http://127.0.0.1:8000/docs 로 접속하면 FastAPI의 자동 생성된 API 문서를 확인할 수 있습니다. /files/uploadfile/ 엔드포인트를 테스트해볼 수 있습니다.

# backend/app/api/files.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import os
import uuid # 고유한 파일 이름 생성을 위해 uuid 사용
from datetime import datetime # 타임스탬프 사용
from dotenv import load_dotenv # .env 파일에서 환경 변수 로드

# S3 서비스 함수 임포트
from ..services.s3_service import upload_file_to_s3

# .env 파일에서 환경 변수 로드
load_dotenv()

# API 라우터 인스턴스 생성. prefix로 /api/v1/files 를 사용하도록 설정할 수 있음.
# router = APIRouter(prefix="/files", tags=["files"])
router = APIRouter() # 일단은 prefix 없이 단순하게 시작합니다. tags는 문서 자동 생성에 유용합니다.


# 환경 변수에서 S3 버킷 이름 가져오기
# .env 파일에 S3_BUCKET_NAME=your-bucket-name 형태로 설정해야 합니다.
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

if not S3_BUCKET_NAME:
    print("경고: S3_BUCKET_NAME 환경 변수가 설정되지 않았습니다. 파일 업로드 기능이 작동하지 않습니다.")
    # 실제 앱에서는 여기서 더 강력한 에러 처리가 필요할 수 있습니다.


@router.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    """
    단일 파일을 업로드하고 S3에 저장합니다.
    """
    if not S3_BUCKET_NAME:
         raise HTTPException(status_code=500, detail="Server configuration error: S3 bucket name is not set.")

    # 업로드된 파일의 원래 이름 가져오기
    original_filename = file.filename

    # S3에 저장될 고유한 객체 이름 생성
    # 예: uploads/사용자ID/현재날짜시간_원본파일명.확장자 (사용자 인증 기능은 아직 없으므로 간단히)
    # 여기서는 간단히 uploads/고유UUID_원본파일명 형태로 만듭니다.
    # 파일 확장자를 유지하도록 합니다.
    file_extension = os.path.splitext(original_filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    s3_object_name = f"uploads/{unique_filename}" # S3 버킷 내 경로/이름

    print(f"파일 업로드 요청 수신: {original_filename}")
    print(f"S3 객체 이름: {s3_object_name}")

    # S3 서비스 함수 호출하여 파일 업로드
    # UploadFile 객체는 비동기(async)로 처리될 수 있지만,
    # boto3의 upload_fileobj는 내부적으로 스레드 풀을 사용하여 비동기처럼 작동하므로 await가 필요 없습니다.
    # 만약 asyncio를 완벽하게 지원하는 async boto3 래퍼를 사용한다면 await가 필요할 수 있습니다.
    s3_url = upload_file_to_s3(file.file, S3_BUCKET_NAME, s3_object_name)
    # file.file은 실제 파일 객체에 접근합니다.

    if s3_url:
        return {"message": f"파일 '{original_filename}'이 성공적으로 업로드 및 저장되었습니다.",
                "s3_url": s3_url,
                "s3_key": s3_object_name}
    else:
        raise HTTPException(status_code=500, detail="파일을 S3에 업로드하는 데 실패했습니다.")

# 여러 파일 업로드를 위한 엔드포인트 (선택 사항)
@router.post("/uploadfiles/")
async def create_upload_files(files: List[UploadFile] = File(...)):
     """
     여러 파일을 업로드하고 S3에 저장합니다.
     """
     if not S3_BUCKET_NAME:
          raise HTTPException(status_code=500, detail="Server configuration error: S3 bucket name is not set.")

     uploaded_results = []
     for file in files:
         original_filename = file.filename
         file_extension = os.path.splitext(original_filename)[1]
         unique_filename = f"{uuid.uuid4()}{file_extension}"
         s3_object_name = f"uploads/{unique_filename}"

         print(f"파일 업로드 요청 수신 (다중): {original_filename}")
         print(f"S3 객체 이름 (다중): {s3_object_name}")

         s3_url = upload_file_to_s3(file.file, S3_BUCKET_NAME, s3_object_name)

         if s3_url:
              uploaded_results.append({
                  "filename": original_filename,
                  "s3_url": s3_url,
                  "s3_key": s3_object_name,
                  "status": "success"
              })
         else:
              uploaded_results.append({
                  "filename": original_filename,
                  "status": "failed",
                  "detail": "S3 업로드 실패"
              })
         # 파일 객체는 사용 후 자동으로 닫히거나, 명시적으로 file.close()를 호출할 수 있습니다.

     return {"uploaded_files": uploaded_results}

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
