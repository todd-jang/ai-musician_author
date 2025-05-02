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
# 분석 작업 목록에 화성 분석 추가
task_payload["analysis_tasks"].append({"type": "analyze_harmony"})
# 필요하다면 형식 분석도 추가
# task_payload["analysis_tasks"].append({"type": "analyze_form"})
