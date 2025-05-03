# Docker Compose로 서비스들을 빌드하고 실행합니다.
# --build: Dockerfile이 변경되었거나 이미지가 없을 경우 다시 빌드합니다.
# -d: 백그라운드에서 실행합니다.
docker-compose up --build -d

ai-1/
├── docker-compose.yml  # 로컬 개발 환경 오케스트레이션
├── .env                # 환경 변수 (AWS/OCI 자격 증명, 버킷 이름 등)
├── traefik/            # (선택) 로컬 또는 환경별 리버스 프록시 설정
│   └── ...
├── frontend/           # 프론트엔드 코드 (컨테이너화)
│   └── ...
├── backend/            # 백엔드 코드 (컨테이너화)
│   └── app/
│       ├── main.py
│       ├── api/        # API 엔드포인트 정의
│       │   └── files.py
│       └── services/   # 외부 시스템 연동 코드 (하이브리드/멀티 클라우드 핵심)
│           ├── __init__.py
│           ├── s3_service.py    # AWS S3 연동
│           ├── onprem.py        # 온프레미스 연동
│           ├── lambda.py        # AWS Lambda 연동
│           ├── oracle.py        # Oracle Cloud 연동
│           └── aws_spot.py      # AWS Spot 워커 연동 (SQS 등)
│   └── requirements.txt
│   └── Dockerfile # 백엔드 컨테이너 빌드 파일
├── db/                 # 데이터베이스 설정 (컨테이너화)
│   └── ...
│   └── Dockerfile
├── infrastructure/     # 인프라스트럭처 관리
│   └── terraform/      # 각 클라우드/환경별 인프라 IaC
│       ├── aws/           # AWS 리전별 인프라 (S3, 네트워크, EKS, VPN 등)
│       │   └── ...tf
│       ├── oracle/        # Oracle Cloud 리전별 인프라 (Object Storage, 네트워크, OKE, FastConnect 등)
│       │   └── ...tf
│       └── onprem/        # 온프레미스 인프라 및 클라우드 연동 설정 (네트워크 장비 설정 등)
│           └── ...tf
│   └── k8s/            # 각 Kubernetes 클러스터별 애플리케이션 배포 매니페스트
│       ├── aws-seoul/     # AWS 서울 리전 클러스터 배포 파일
│       │   └── ...yaml
│       ├── onprem/        # 온프레미스 클러스터 배포 파일
│       │   └── ...yaml
│       └── oracle-ashburn/ # Oracle Ashburn 리전 클러스터 배포 파일
│           └── ...yaml
│   └── monitoring/     # 모니터링/로깅 설정
│       └── ...

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

# backend/app/services/lambda.py

import boto3
import json
import os

# AWS Lambda 클라이언트 생성
lambda_client = boto3.client("lambda")

# 처리 워커 Lambda 함수 이름 (환경 변수 등에서 설정)
PROCESSING_LAMBDA_NAME = os.getenv("PROCESSING_LAMBDA_NAME", "your-processing-lambda-function")

class LambdaService:
    """
    AWS Lambda 함수와 연동하는 클래스 예시
    """
    def invoke_processing_lambda(self, payload: dict):
        """
        PDF 처리 Lambda 함수를 비동기적으로 호출합니다.
        """
        if not PROCESSING_LAMBDA_NAME:
            print("경고: PROCESSING_LAMBDA_NAME 환경 변수가 설정되지 않았습니다.")
            return None

        print(f"Lambda 함수 ({PROCESSING_LAMBDA_NAME}) 호출 시도 (비동기)...")
        try:
            # InvocationType='Event'는 비동기 호출 (응답 기다리지 않음)
            # InvocationType='RequestResponse'는 동기 호출 (응답 기다림)
            response = lambda_client.invoke(
                FunctionName=PROCESSING_LAMBDA_NAME,
                InvocationType='Event', # 비동기 호출 예시
                Payload=json.dumps(payload)
            )
            print(f"Lambda 호출 응답 (비동기): 상태 코드 {response['StatusCode']}")

            # 비동기 호출 시에는 FunctionError가 발생해도 여기서 바로 알 수 없을 수 있음
            # 응답 본문이 비어 있거나 짧음
            return {"status": "invocation_successful", "response_code": response['StatusCode']}

        except Exception as e:
            print(f"Lambda 호출 오류 (예시): {e}")
            return None
        # TODO: 실제 Lambda 연동 코드 구현

    def get_lambda_status(self, invocation_id: str):
         """
         (동기 호출 시) 특정 Lambda 호출의 상태나 결과를 조회합니다.
         (비동기 호출 시에는 다른 메커니즘 필요 - 예: Step Functions, DB 상태 조회)
         """
         print(f"Lambda 호출 상태 조회 시도 (예시): {invocation_id}")
         # TODO: 실제 상태 조회 로직 구현 (매우 복잡할 수 있음)
         return {"invocation_id": invocation_id, "status": "unknown"} # Mock 응답


# 서비스 인스턴스 생성
lambda_service = LambdaService()

# 사용 예시:
# s3_key = "uploads/..."
# lambda_service.invoke_processing_lambda({"s3_key": s3_key, "source_bucket": "your-bucket"})

# backend/app/services/oracle.py

# import oci # Oracle Cloud Infrastructure SDK for Python

# Oracle Cloud 접속 정보 (환경 변수나 설정을 통해 관리)
# OCI_CONFIG_FILE = os.getenv("OCI_CONFIG_FILE", "~/.oci/config")
# OCI_PROFILE = os.getenv("OCI_PROFILE", "DEFAULT")
# OCI_NAMESPACE = os.getenv("OCI_NAMESPACE", "your-oci-namespace")
# OCI_BUCKET_NAME = os.getenv("OCI_BUCKET_NAME", "your-oci-bucket")
# OCI_AI_SERVICE_ENDPOINT = os.getenv("OCI_AI_SERVICE_ENDPOINT", "...")


class OracleCloudService:
    """
    Oracle Cloud Infrastructure 서비스와 연동하는 클래스 예시
    """
    def upload_file_to_oci_storage(self, file_object, bucket_name: str, object_name: str):
        """
        파일 객체를 Oracle Cloud Infrastructure Object Storage에 업로드합니다.
        (실제 OCI SDK 코드로 대체 필요)
        """
        print(f"Oracle Cloud Storage ({bucket_name}/{object_name}) 업로드 시도 (예시)...")
        # 예시: oci.object_storage.ObjectStorageClient 사용
        # try:
        #     config = oci.config.from_file(OCI_CONFIG_FILE, OCI_PROFILE)
        #     object_storage_client = oci.object_storage.ObjectStorageClient(config)
        #
        #     put_object_response = object_storage_client.put_object(
        #         namespace_name=OCI_NAMESPACE,
        #         bucket_name=bucket_name,
        #         object_name=object_name,
        #         put_object_body=file_object # 파일 객체 또는 스트림
        #     )
        #     print("OCI Storage 업로드 성공 (예시)")
        #     return f"oci://{bucket_name}/{object_name}" # 예시 URL 형식
        # except Exception as e:
        #     print(f"OCI Storage 업로드 오류 (예시): {e}")
        #     return None
        # TODO: 실제 OCI Object Storage 연동 코드 구현
        return f"oci://{bucket_name}/{object_name}" # Mock URL 반환


    def perform_oracle_ai_inference(self, data_payload: dict):
        """
        Oracle Cloud의 특정 AI 서비스에서 추론 작업을 수행합니다.
        """
        print(f"Oracle AI 서비스 추론 요청 시도 (예시): {data_payload}")
        # 예시: oci.ai_language.AIServiceLanguageClient 또는 특정 AI 서비스 클라이언트 사용
        # try:
        #     config = oci.config.from_file(OCI_CONFIG_FILE, OCI_PROFILE)
        #     ai_client = oci.ai_language.AIServiceLanguageClient(config)
        #     # 추론 요청 API 호출
        #     # response = ai_client.analyze_text(...)
        #     print("Oracle AI 추론 성공 (예시)")
        #     return {"result": "analysis result from Oracle AI"} # 예시 결과
        # except Exception as e:
        #     print(f"Oracle AI 추론 오류 (예시): {e}")
        #     return None
        # TODO: 실제 Oracle AI 서비스 연동 코드 구현
        return {"result": "analysis result from Oracle AI (mock)"} # Mock 결과

# 서비스 인스턴스 생성
oracle_cloud_service = OracleCloudService()

# 사용 예시:
# # OCI Storage 사용 시 (파일 업로드 부분에서 S3 대신 호출)
# # oci_url = oracle_cloud_service.upload_file_to_oci_storage(file.file, OCI_BUCKET_NAME, "uploads/oci/...")
#
# # Oracle AI 서비스 사용 시 (분석 워커에서 호출)
# # analysis_result = oracle_cloud_service.perform_oracle_ai_inference({"text": "...", "language": "en"})
# backend/app/services/aws_spot.py

import boto3
import os
# import json
# from botocore.exceptions import ClientError

# AWS EC2 클라이언트 (Spot 인스턴스 관련 작업 시 필요)
# ec2_client = boto3.client("ec2")
# # 메시지 큐 서비스 클라이언트 (예: SQS, Spot 인스턴스 워커가 큐를 읽는 경우)
# sqs_client = boto3.client("sqs")

# 워커 통신 관련 정보 (환경 변수 등에서 설정)
# WORKER_SQS_QUEUE_URL = os.getenv("WORKER_SQS_QUEUE_URL", "your-worker-sqs-queue-url")


class AwsSpotService:
    """
    AWS Spot 인스턴스 기반 워커 또는 관련 AWS 서비스와 연동하는 클래스 예시
    (Lambda 서비스와 유사하거나 보완적인 역할)
    """
    def send_task_to_spot_worker(self, task_payload: dict):
        """
        Spot 인스턴스 기반 워커에게 처리 작업을 지시합니다.
        (예: SQS 큐에 메시지 발행)
        """
        # if not WORKER_SQS_QUEUE_URL:
        #      print("경고: WORKER_SQS_QUEUE_URL 환경 변수가 설정되지 않았습니다.")
        #      return None

        print(f"Spot 워커에게 작업 전송 시도 (SQS 예시): {task_payload}")
        # try:
        #     response = sqs_client.send_message(
        #         QueueUrl=WORKER_SQS_QUEUE_URL,
        #         MessageBody=json.dumps(task_payload)
        #     )
        #     print(f"SQS 메시지 전송 성공 (예시): 메시지 ID {response.get('MessageId')}")
        #     return {"status": "task_sent_to_sqs", "message_id": response.get('MessageId')}
        # except ClientError as e:
        #     print(f"SQS 메시지 전송 오류 (예시): {e}")
        #     return None
        # TODO: 실제 Spot 워커 연동 코드 구현 (SQS, SNS, 직접 API 호출 등)
        return {"status": "task_sent_to_spot_worker_queue (mock)"} # Mock 응답


    def request_spot_instance(self, instance_config: dict):
        """
        필요에 따라 Spot 인스턴스를 요청합니다. (처리량이 많을 때 동적 확장)
        """
        print(f"Spot 인스턴스 요청 시도 (예시): {instance_config}")
        # 예시: ec2_client.request_spot_instances 사용
        # TODO: 실제 Spot 인스턴스 요청 로직 구현 (매우 복잡할 수 있음 - AMI, 인스턴스 타입, 입찰가 등 설정)
        return {"status": "spot_instance_request_submitted (mock)"} # Mock 응답

# 서비스 인스턴스 생성
aws_spot_service = AwsSpotService()

# 사용 예시:
# # 파일이 S3에 업로드된 후 워커에게 알림
# # s3_key = "uploads/..."
# # aws_spot_service.send_task_to_spot_worker({"s3_key": s3_key, "analysis_type": "pdf_text"})
#
# # 특정 조건에서 워커 확장을 위해 Spot 인스턴스 추가 요청
# # aws_spot_service.request_spot_instance({"instance_type": "c6g.xlarge", "target_capacity": 1})

실행 확인:

컨테이너 상태 확인:

Bash

docker ps
실행 중인 컨테이너 목록(backend, worker, db, redis, (활성화했다면 traefik))이 보일 것입니다.

컨테이너 로그 확인:
각 컨테이너의 실행 로그를 확인하여 오류가 없는지, 정상적으로 시작되었는지 확인합니다.

Bash

docker logs backend
docker logs worker
docker logs db
docker logs redis
backend 로그에 "Application startup complete."와 같은 메시지가 보이면 정상입니다. worker 로그에는 SQS 큐 연결 시도 메시지나 예시 작업 처리 메시지 등이 나타날 수 있습니다. db 로그에는 PostgreSQL 시작 메시지가 보일 것입니다.

백엔드 API 접속 테스트:
웹 브라우저나 curl 명령어를 사용하여 백엔드 API에 접속해 봅니다.

# 예시: curl 명령어로 파일 업로드 테스트
# -F "file=@/path/to/your/sheetmusic.pdf" : 업로드할 파일 지정 (실제 파일 경로 사용)
# -F "output_format=mp3" : 원하는 출력 형식 옵션
# -F "translate_shakespearean=true" : 번역 옵션
curl -X POST -F "file=@/path/to/your/test_file.pdf" \
-F "output_format=midi" \
-F "translate_shakespearean=true" \
http://localhost:8000/music/upload_sheetmusic/
FastAPI 자동 문서: http://localhost:8000/docs 로 접속합니다. FastAPI가 제공하는 Swagger UI 기반의 API 문서를 볼 수 있습니다. /music/upload_sheetmusic/ 엔드포인트를 확인하고 테스트해 볼 수 있습니다.
루트 엔드포인트: curl http://localhost:8000/ 명령 실행 시 {"message":"Personal Data Assistant Backend is running!"} 와 같은 응답이 오는지 확인합니다.
파일 업로드 테스트: /music/upload_sheetmusic/ 엔드포인트에 악보 파일 (또는 아무 파일)을 업로드하는 테스트를 수행합니다.

업로드 성공 시 {"message": "Sheet music uploaded and processing requested.", ...}와 같은 응답을 받을 것입니다.

워커 작업 확인:
파일 업로드 후 worker 컨테이너의 로그를 다시 확인합니다.

Bash

docker logs worker
백엔드가 보낸 task_payload를 워커가 수신하고 처리하려는 로그 메시지가 보일 것입니다. (실제 OMR, 음악 생성, GPT 호출 등이 작동하려면 해당 라이브러리 설치 및 설정, API 키 설정 등이 필요하며, 로컬 Redis가 아닌 실제 SQS 큐를 사용하도록 설정해야 할 수 있습니다.)

Docker Compose 중지:

테스트를 마쳤으면 다음 명령으로 모든 서비스 컨테이너를 중지하고 제거합니다.

Bash

docker-compose down
볼륨 데이터는 기본적으로 유지되지만, -v 옵션을 추가하면 볼륨 데이터까지 제거합니다 (docker-compose down -v).

이제 백엔드 서비스와 워커 서비스가 컨테이너화되었고, Docker Compose를 사용하여 로컬 개발 환경에서 함께 실행하고 기본적인 통합 테스트를 수행할 수 있습니다. 이는 MVP를 위한 배포 가능한 형태의 기반이 됩니다.

-------------------------------------------------------------------
--- Final Integrated Performance Testing ---

Okay, let's focus on building the foundation for the final integrated performance testing. This involves three key areas: setting up the performance test environment, defining realistic load scenarios, and ensuring the integrated monitoring system is fully functional.

### 1. 성능 테스트 환경 구축 (Performance Test Environment Setup)

성능 테스트 환경은 **실제 운영 환경을 가장 근접하게 모방**하는 것이 목표입니다. 이는 단순한 기능 테스트 환경보다 더 많은 자원을 요구하며, 하이브리드 멀티 클라우드 아키텍처의 복잡성을 그대로 반영해야 합니다.

**주요 원칙:**

* **IaC 사용:** `infrastructure/terraform/` 코드를 사용하여 인프라를 프로비저닝합니다. 이는 환경 간 일관성을 보장하고 반복 가능한 테스트 환경 구축을 가능하게 합니다.
* **운영 환경 규모 반영:** 예상되는 **최대 피크 부하**를 처리할 수 있도록 VM 크기, DB 인스턴스 티어, SQS 처리량, 스토리지 용량 등을 운영 환경의 계획에 맞춰 설정합니다.
* **실제 서비스 사용:** 가능하면 관리형 서비스(RDS, OCI Autonomous DB, SQS, S3/Object Storage 등)를 사용하고, 온프레미스 구성 요소가 있다면 포함시킵니다. Mock 서비스는 특정 시뮬레이션 단계에서 사용되었지만, 최종 성능 테스트에서는 실제 서비스를 대상으로 해야 합니다.
* **크로스 클라우드 네트워킹:** 클라우드 간, 클라우드와 온프레미스 간의 네트워크 연결(VPN, 전용선) 및 방화벽/보안 그룹 설정이 실제와 동일하게 구성되어야 합니다.

**`infrastructure/terraform/`에서의 설정:**

Terraform 변수(`variables.tf`)를 활용하여 환경별 설정 값을 유연하게 관리합니다. 운영 환경과 성능 테스트 환경은 변수 파일만 바꿔서 동일한 코드로 프로비저닝할 수 있도록 설계합니다.

* **VM/Node 수:** 워커 서비스가 배포될 Kubernetes 클러스터의 Node 수나 VM 수를 피크 부하를 고려하여 설정합니다. (예: `worker_node_count` 변수)
* **VM 사양:** Node 또는 VM의 CPU, 메모리 사양을 설정합니다. (예: `worker_vm_type` 변수)
* **DB 인스턴스 크기/티어:** 데이터베이스의 성능 티어 또는 인스턴스 크기를 설정합니다. (예: `db_instance_tier` 변수)
* **SQS/Storage 설정:** 필요시 SQS 처리량, Storage 서비스의 성능 옵션 등을 설정합니다.
* **네트워크 구성:** VPC CIDR, 서브넷, 보안 그룹, 라우팅 설정, 크로스 클라우드 연결 설정 등을 정의합니다.

```terraform
# infrastructure/terraform/aws/variables.tf (예시 - 성능 테스트 환경용 변수)

variable "environment" {
  description = "The deployment environment (e.g., dev, test, perf, prod)."
  type        = string
  default     = "perf" # 성능 테스트 환경

}

# EC2 인스턴스 또는 EKS 노드 그룹 설정
variable "worker_node_count" {
  description = "Number of worker nodes/VMs for the performance test environment."
  type        = number
  default     = 10 # 예: 성능 테스트를 위해 10대의 워커 노드 사용
}

variable "worker_vm_type" {
  description = "EC2 instance type for worker nodes."
  type        = string
  default     = "m5.xlarge" # 예: 워커 노드 VM 사양

}

# RDS PostgreSQL 설정
variable "db_instance_tier" {
  description = "RDS PostgreSQL instance class (performance tier)."
  type        = string
  default     = "db.m5.large" # 예: 성능 테스트 DB 티어

}

# SQS 처리량 설정 (필요시)
# variable "sqs_throughput_mode" { ... }

# 다른 필요한 변수 (VPC CIDR, 서브넷, S3 버킷 이름, 알림 이메일 등) 정의
# ...
