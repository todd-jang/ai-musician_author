# backend/app/api/files.py

from fastapi import APIRouter, UploadFile, File, HTTPException # List는 이제 필요 없습니다.
# from typing import List # 여러 파일 업로드 엔드포인트를 제거했으므로 필요 없습니다.
import os
import uuid # 고유한 파일 이름 생성을 위해 uuid 사용
from datetime import datetime # 타임스탬프 사용
from dotenv import load_dotenv # .env 파일에서 환경 변수 로드

# S3 서비스 함수 임포트 (파일 업로드용)
from ..services.s3_service import upload_file_to_s3

# 워커에게 작업을 지시할 서비스 임포트 (예시: SQS로 메시지 보내는 서비스)
# 이 함수는 task_payload를 SQS 큐에 발행하는 역할을 합니다.
from ..services.aws_spot import send_task_to_spot_worker_queue

# .env 파일에서 환경 변수 로드
load_dotenv()

# API 라우터 인스턴스 생성. 악보/음악 관련 엔드포인트이므로 prefix를 /music으로 설정합니다.
router = APIRouter(prefix="/music", tags=["music"])


# 환경 변수에서 S3 버킷 이름 가져오기 (파일 저장 스토리지)
# .env 파일에 S3_BUCKET_NAME=your-bucket-name 형태로 설정해야 합니다.
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# 워커 서비스가 파일을 다운로드할 때 필요한 스토리지 설정 (버킷 종류, 버킷 이름)
# 이 정보는 워커에게 task_payload를 통해 전달됩니다.
STORAGE_CONFIG = {
    "type": os.getenv("STORAGE_TYPE", "s3"), # 기본값 S3. .env에서 STORAGE_TYPE 설정 가능
    "bucket_name": S3_BUCKET_NAME
    # TODO: OCI, On-Premise 등 다른 스토리지 타입 사용 시 해당 설정 추가
}


if not STORAGE_CONFIG["bucket_name"]:
    print(f"경고: 스토리지 버킷 이름이 설정되지 않았습니다 (타입: {STORAGE_CONFIG.get('type', 'unknown')}). 파일 업로드 및 작업 지시 기능이 작동하지 않습니다.")


@router.post("/upload_sheetmusic/") # 악보 업로드용으로 엔드포인트 이름 변경
async def upload_sheet_music(
    file: UploadFile = File(...),
    output_format: str = "midi", # 원하는 음악 파일 출력 형식 (midi, mp3)
    translate_shakespearean: bool = False # 셰익스피어 문체 번역 필요 여부 (기본값 False)
):
    """
    악보 파일을 업로드하고, 음악 생성 및 처리를 위해 워커에게 작업을 지시합니다.
    업로드된 파일은 S3에 저장되고, 작업 요청은 SQS 큐로 전송됩니다.
    """
    # 스토리지 설정 확인
    if not STORAGE_CONFIG["bucket_name"]:
         raise HTTPException(
              status_code=500,
              detail=f"Server configuration error: Storage bucket name is not set for type {STORAGE_CONFIG.get('type', 'unknown')}."
          )
    
    # 지원하는 파일 형식인지 확인 (선택 사항이지만 좋은 관행)
    allowed_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.musicxml', '.mxl', '.mid']
    original_filename = file.filename
    if not original_filename:
        raise HTTPException(status_code=400, detail="No file name provided.")
        
    file_extension = os.path.splitext(original_filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_extension}. Supported formats are: {', '.join(allowed_extensions)}"
        )

    # S3에 저장될 고유한 객체 이름 생성
    # 예: sheetmusic/task_id/원본파일명.확장자
    task_id = str(uuid.uuid4()) # 이번 작업에 대한 고유 ID
    # 파일 확장자를 유지하고, task_id를 경로에 포함시켜 관리 용이
    s3_object_name = f"sheetmusic/{task_id}/{os.path.basename(original_filename)}" # S3 버킷 내 경로/이름

    print(f"악보 파일 업로드 요청 수신: {original_filename}")
    print(f"생성된 작업 ID: {task_id}")
    print(f"S3 객체 이름 (예정): {s3_object_name}")
    print(f"요청된 출력 형식: {output_format}")
    print(f"셰익스피어 번역 요청: {translate_shakespearean}")


    s3_url = None
    try:
        # 1. 악보 파일을 S3에 업로드
        # file.file은 SpooledTemporaryFile 객체이며, boto3 upload_fileobj에 직접 전달 가능
        print(f"S3에 파일 업로드 시도: 버킷={STORAGE_CONFIG['bucket_name']}, 키={s3_object_name}")
        s3_url = upload_file_to_s3(file.file, STORAGE_CONFIG["bucket_name"], s3_object_name)

        if not s3_url:
             raise RuntimeError("S3 파일 업로드 실패")
        print(f"악보 파일 S3 업로드 성공: {s3_url}")

        # 2. 워커에게 전달할 작업 페이로드 (JSON) 생성
        task_payload = {
            "task_id": task_id, # 워커가 이 ID를 사용하여 작업 추적 및 결과 보고
            "file_location": {
                "type": STORAGE_CONFIG["type"], # 스토리지 타입 (s3, oci, onprem 등)
                "bucket": STORAGE_CONFIG["bucket_name"], # 버킷 이름 (S3, OCI 등)
                "key": s3_object_name # 스토리지 내 객체 키/경로
                # TODO: On-Premise 파일의 경우, 워커가 접근할 수 있는 다른 식별자나 경로 필요
            },
            # 워커가 수행할 단계 목록 정의 (순서 고려)
            "processing_steps": [
                {"type": "extract_music_data"}, # 악보 데이터 추출 (입력 파일 형식에 따라 OMR 포함)
                {"type": "extract_text_from_score"}, # 악보 데이터에서 텍스트 추출 (가사, 지시어 등)
                {"type": "generate_music_file", "output_format": output_format}, # 음악 파일 생성 (MIDI 또는 MP3)
            ],
            "analysis_tasks": [], # 텍스트 분석/번역 작업 목록
            "metadata": {
                 "original_filename": original_filename,
                 "original_file_extension": file_extension,
                 "uploaded_at": datetime.utcnow().isoformat(),
                 "requested_output_format": output_format,
                 "request_shakespearean_translation": translate_shakespearean
            }
        }

        # 셰익스피어 번역이 필요한 경우 분석 작업 목록에 추가
        if translate_shakespearean:
            # 셰익스피어 번역 분석 작업 추가
            task_payload["analysis_tasks"].append({"type": "translate_to_shakespearean"})
            # 필요하다면 다른 분석 작업도 여기에 추가 (예: {"type": "analyze_harmony"})

        # 3. 작업 페이로드를 워커 서비스에게 지시 (SQS 메시지 발행)
        print(f"워커에게 작업 지시 시도 (task_id: {task_id})")
        # send_task_to_spot_worker_queue 함수는 backend/app/services/aws_spot.py에 구현되어 SQS 메시지를 보냅니다.
        message_response = send_task_to_spot_worker_queue(task_payload)

        if message_response and message_response.get("status") == "task_sent_to_sqs":
            print(f"작업 지시 성공: 메시지 ID = {message_response.get('message_id')}. Task ID = {task_id}")
            # TODO: 데이터베이스에 작업 상태 초기 기록 (task_id, status="queued", upload_url 등)
            # from ..services.db_service import create_task_entry
            # create_task_entry(task_id=task_id, status="queued", file_location=task_payload["file_location"], metadata=task_payload["metadata"])

            # 4. 사용자에게 작업 접수 응답 반환
            return {
                "message": "Sheet music uploaded and processing requested.",
                "task_id": task_id, # 사용자에게 작업 ID 반환하여 상태 조회에 사용하도록 함
                "uploaded_s3_key": s3_object_name, # 업로드된 파일 위치 정보
                "status": "processing_queued" # 작업이 큐에 들어갔음을 알림
            }
        else:
            # 메시지 전송 실패 시
            print("오류: 워커에게 작업 지시 실패")
            # TODO: S3에 업로드된 파일 롤백하거나, 실패 상태를 데이터베이스에 기록하는 등 후처리 필요
            raise HTTPException(status_code=500, detail="Failed to queue processing task.")

    except HTTPException as e:
        # FastAPI HTTPException 재발생
        raise e
    except Exception as e:
        print(f"파일 업로드 및 작업 지시 중 오류 발생: {e}")
        # TODO: 실패 시 로깅 및 사용자 알림
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")


# TODO: 작업 상태 조회 엔드포인트 추가 (/music/status/{task_id})
# @router.get("/status/{task_id}")
# async def get_task_status(task_id: str):
#     """특정 작업 ID의 현재 상태를 조회합니다."""
#     # TODO: 데이터베이스 등에서 task_id로 작업 상태 조회 및 결과 정보 반환
#     # 예: from ..services.db_service import get_task_status_by_id
#     # task_info = get_task_status_by_id(task_id)
#     # if not task_info:
#     #     raise HTTPException(status_code=404, detail="Task not found")
#     # return task_info # {"task_id": "...", "status": "...", "results_url": "...", ...}
#     return {"task_id": task_id, "status": "placeholder", "detail": "Status check not yet implemented"}


# TODO: 결과 파일 다운로드 엔드포인트 추가 (/music/results/{task_id}/{file_type})
# @router.get("/results/{task_id}/{file_type}")
# async def download_result_file(task_id: str, file_type: str):
#     """완료된 작업의 결과 파일을 다운로드합니다."""
#     # TODO: 데이터베이스에서 task_id와 file_type으로 결과 파일 S3 키/URL 조회
#     # 예: from ..services.db_service import get_task_result_location
#     # result_location = get_task_result_location(task_id, file_type)
#     # if not result_location or result_location["status"] != "success":
#     #      raise HTTPException(status_code=404, detail=f"Result file ({file_type}) not found or processing failed for task {task_id}")
#
#     # S3 등에서 파일 스트리밍 다운로드하여 응답으로 제공
#     # 예: from ..services.s3_service import stream_file_from_s3
#     # from fastapi.responses import StreamingResponse
#     # media_type = "audio/midi" if file_type == "midi" else "audio/mpeg" if file_type == "mp3" else "application/octet-stream"
#     # return StreamingResponse(stream_file_from_s3(STORAGE_CONFIG["bucket_name"], result_location["s3_key"]), media_type=media_type)
#     return {"detail": "Result download not yet implemented"}
