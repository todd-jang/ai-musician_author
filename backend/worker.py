# backend/app/worker.py

import json
import os
import time
import uuid # 결과 파일 이름 등에 사용될 수 있음

# 파일 다운로드 서비스 임포트 (상대 경로 사용)
# backend/app/services 디렉토리의 모듈을 임포트합니다.
from .services.s3_service import download_file_from_s3 # S3 다운로드 함수가 있다고 가정

# PDF 텍스트 추출 라이브러리 임포트
from pdfminer.high_level import extract_text as pdf_extract_text

# LangChain 및 OpenAI 라이브러리 임포트
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.document_loaders import TextLoader # 텍스트 추출 후 필요 시 사용
from langchain.text_splitter import CharacterTextSplitter # 긴 텍스트 처리 시 필요

# .env 파일에서 환경 변수 로드 (API 키 등)
from dotenv import load_dotenv
load_dotenv()

# OpenAI API 키 설정 (환경 변수 OPENAI_API_KEY 로 설정 권장)
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# 데이터베이스 저장 서비스 임포트 (결과 저장 시 필요)
# from .services.db_service import save_analysis_result # 아직 만들지 않은 가정의 서비스

# 워커가 사용할 스토리지 설정 (main.py와 동일하게 환경 변수에서 로드)
# 실제 배포 시에는 워커의 환경 변수로 별도 주입됩니다.
STORAGE_CONFIG = {
    "type": os.getenv("STORAGE_TYPE", "s3"), # 기본값 S3
    "bucket_name": os.getenv("S3_BUCKET_NAME") # S3를 사용하는 경우
    # OCI나 온프레미스인 경우 해당 설정 로드
}


# 워커의 진입점 함수 예시 (메시지 큐 리스너, Lambda 핸들러 등에 의해 호출될 함수)
# 이 함수는 task_payload라는 딕셔너리를 입력으로 받습니다.
# task_payload는 main.py에서 생성되어 메시지 큐를 통해 전달됩니다.
def process_task(task_payload: dict):
    """
    주어진 작업 페이로드를 처리합니다.
    이 함수는 메시지 큐에서 메시지를 받거나 Lambda 이벤트로 트리거될 때 호출됩니다.

    :param task_payload: 처리할 작업 내용이 담긴 딕셔너리 (JSON 파싱 결과)
                         예: {"task_id": "...",
                              "file_location": {"type": "s3", "bucket": "...", "key": "..."},
                              "processing_steps": [...], # 예: OMR, 음악 생성
                              "analysis_tasks": [...], # 예: 셰익스피어 번역
                              "metadata": {...}
                             }
    :return: 처리 결과 딕셔너리
    """
    task_id = task_payload.get("task_id", "unknown-task")
    print(f"\n>>> 워커: 작업 수신 (Task ID: {task_id})")
    start_time = time.time()

    file_location = task_payload.get("file_location")
    processing_steps = task_payload.get("processing_steps", [])
    analysis_tasks = task_payload.get("analysis_tasks", [])
    metadata = task_payload.get("metadata", {})

    processed_results = {"task_id": task_id, "metadata": metadata}
    overall_status = "processing"

    downloaded_file_path = None
    music_data_representation = None
    extracted_text = None

    try:
        # --- 1. 파일 다운로드 단계 ---
        if file_location and "type" in file_location and "key" in file_location:
            file_type = file_location["type"]
            file_key = file_location["key"]
            bucket_name = file_location.get("bucket")

            print(f"워커: 파일 다운로드 시도: 타입={file_type}, 키={file_key}")
            try:
                # TODO: 실제 다운로드 로직 구현 (S3, OCI, 온프레미스)
                if file_type == "s3":
                    if not bucket_name: raise ValueError("S3 파일 위치는 버킷 이름이 필요합니다.")
                    downloaded_file_path = f"/tmp/{task_id}_{os.path.basename(file_key)}"
                    s3_client = boto3.client('s3')
                    s3_client.download_file(bucket_name, file_key, downloaded_file_path)
                    print("워커: S3 파일 다운로드 성공.")
                elif file_type == "oci":
                     # TODO: OCI 다운로드 로직
                     downloaded_file_path = f"/tmp/{task_id}_{os.path.basename(file_key)}"
                     print("워커: OCI 파일 다운로드 성공 (예시).")
                     pass # OCI SDK 사용
                elif file_type == "onprem":
                     # TODO: 온프레미스 파일 접근 로직
                     downloaded_file_path = file_key # 직접 접근 가능하다고 가정
                     if not os.path.exists(downloaded_file_path): raise FileNotFoundError(f"온프레미스 파일 찾을 수 없음: {downloaded_file_path}")
                     print("워커: 온프레미스 파일 접근 확인.")
                     pass
                else:
                     raise ValueError(f"워커: 지원하지 않는 파일 위치 타입: {file_type}")

                if not downloaded_file_path: raise RuntimeError("워커: 파일 다운로드 경로 설정 실패.")
                processed_results["downloaded_file"] = {"path": downloaded_file_path, "type": file_type}

            except Exception as e:
                print(f"워커: 파일 다운로드 중 오류 발생: {e}")
                processed_results["download_error"] = str(e)
                overall_status = "failed"
                # 파일 다운로드 실패 시 이후 처리는 무의미하므로 여기서 종료
                raise e # 예외를 다시 발생시켜 finally 블록으로 이동

        else:
            print("워커: 작업 페이로드에 파일 위치 정보가 없습니다.")
            processed_results["download_error"] = "Missing file location in payload"
            overall_status = "failed"
            raise ValueError("Missing file location")


        # --- 2. 처리 단계 실행 (processing_steps + analysis_tasks) ---
        # 각 단계를 순서대로 실행합니다.
        # 음악 처리와 텍스트 처리가 서로 의존적일 수 있으므로 순서 고려가 중요합니다.

        for step in processing_steps + analysis_tasks: # 모든 단계를 합쳐 순회
            step_type = step.get("type")
            print(f"워커: 작업 단계 '{step_type}' 실행 시도...")
            step_success = False

            try:
                if step_type == "extract_music_data":
                    if downloaded_file_path:
                        print("워커: 악보 데이터 추출 (OMR/파싱) 시작...")
                        # TODO: OMR/파싱 로직 구현. 결과는 music_data_representation에 저장.
                        # 예: music_data_representation = perform_omr(downloaded_file_path)
                        music_data_representation = {"notes_data": "...", "text_elements": ["Lyric1", "Lyric2"]} # Mock 결과
                        print("워커: 악보 데이터 추출 완료 (예시).")
                        processed_results["music_data_extraction"] = {"status": "success"}
                        step_success = True
                    else:
                        print("워커: 다운로드된 파일이 없어 악보 데이터 추출 건너뜁니다.")


                elif step_type == "extract_text_from_score":
                     if "music_data_extraction" in processed_results and music_data_representation:
                          print("워커: 악보 데이터에서 텍스트 추출 시작...")
                          # TODO: music_data_representation에서 텍스트 요소 추출 로직 구현
                          # 예: extracted_text = extract_text_from_music_data(music_data_representation)
                          extracted_text = "Extracted lyrics here. Andante con moto." # Mock 텍스트
                          print("워커: 텍스트 추출 완료 (예시).")
                          processed_results["text_extraction"] = {"status": "success", "extracted_text_length": len(extracted_text)}
                          step_success = True
                     else:
                          print("워커: 악보 데이터가 없거나 추출 단계 실패로 텍스트 추출 건너뜁니다.")


                elif step_type == "translate_to_shakespearean":
                    # 셰익스피어 문체 번역 (LangChain/GPT 사용)
                    if extracted_text and extracted_text.strip():
                        print("워커: 셰익스피어 문체 번역 시작...")
                        # --- LangChain/GPT 번역 코드 ---
                        prompt_template = """Translate the following text into English,
                        and then rewrite the translated text in the style of William Shakespeare.
                        Original Text: "{original_text}"
                        Shakespearean Style Translation:"""

                        PROMPT = PromptTemplate(input_variables=["original_text"], template=prompt_template)
                        llm = ChatOpenAI(model=task_payload.get("model", "gpt-3.5-turbo"), temperature=0.7)
                        chain = LLMChain(llm=llm, prompt=PROMPT)

                        try:
                            # 실제 구현 시 토큰 제한 고려 분할 처리 필수!
                            text_to_translate = extracted_text # 추출된 텍스트 사용
                            if len(text_to_translate) > 3000:
                                 text_to_translate = text_to_translate[:3000] + "..."

                            shakespearean_text = chain.run(original_text=text_to_translate)

                            processed_results["shakespearean_translation"] = {
                               "status": "success",
                               "original": text_to_translate,
                               "translated": shakespearean_text.strip()
                            }
                            print("워커: 셰익스피어 문체 번역 완료.")
                            step_success = True

                        except Exception as e:
                            print(f"워커: 셰익스피어 문체 번역 오류: {e}")
                            processed_results["shakespearean_translation"] = {"status": "failed", "error": str(e)}
                            # 실패했지만 전체 작업 중단은 아님

                    else:
                        print("워커: 번역할 텍스트가 없어 셰익스피어 문체 번역 건너뜁니다.")
                        processed_results["shakespearean_translation"] = {"status": "skipped", "message": "No text found for translation"}
                        step_success = True

                # backend/app/worker.py (process_task 함수 내부, 작업 단계 실행 루프 안)

# ... (all_tasks 순회 루프 시작 및 기존 단계들 유지) ...

        try:
            # ... (기존 단계들: extract_music_data, extract_text_from_score, translate_to_shakespearean, generate_music_file 등) ...

            elif step_type == "analyze_harmony":
                # 화성 분석 로직 구현
                if isinstance(music_data_representation, stream.Stream):
                    print("워커: 화성 분석 시작 (Music21 예시)...")
                    step_status = "processing"
                    try:
                        # Music21의 화성 분석 모듈 사용
                        # analyze() 메소드는 Stream에 직접 적용하거나 analysis.harmony 모듈 사용
                        # 예시: 화음 분석 결과를 Stream에 삽입
                        # harmony_analyzer = analysis.harmony.HarmonicAnalysis(music_data_representation)
                        # harmony_analyzer.analyze()
                        # analysis_results_stream = harmony_analyzer.music21Object # 분석 결과가 포함된 Music21 Stream

                        # 간단한 화음 리스트 추출 예시
                        chords = music_data_representation.flat.getElementsByClass('Chord')
                        harmony_list = []
                        for ch in chords:
                            try:
                                # 화음의 근음과 형태 분석
                                root_pitch = ch.root()
                                quality = ch.quality()
                                harmony_name = f"{root_pitch.name} {quality}"
                                harmony_list.append({
                                    "offset": ch.offset, # 악보 내 위치
                                    "chord": ch.pitchedCommonNames, # 구성음 이름
                                    "harmony": harmony_name # 분석된 화음 이름
                                })
                            except Exception as e:
                                 # 분석 불가능한 화음 등 오류 처리
                                 print(f"워커: 화음 분석 오류 발생: {e}")
                                 harmony_list.append({
                                      "offset": ch.offset,
                                      "chord": ch.pitchedCommonNames,
                                      "harmony": "Analysis Failed",
                                      "error": str(e)
                                 })


                        print(f"워커: 화성 분석 완료. 총 {len(harmony_list)}개 화음 분석.")
                        processed_results["harmony_analysis"] = {
                            "status": "success",
                            "results": harmony_list
                        }
                        step_status = "success"

                    except Exception as e:
                        print(f"워커: 화성 분석 중 오류 발생: {e}", exc_info=True)
                        step_status = "failed"
                        processed_results[f"{step_type}_error"] = str(e)

                else:
                    print("워커: Music21 Stream 객체가 없어 화성 분석 건너뜁니다.")
                    step_status = "skipped"

                processed_results[f"{step_type}_status"] = step_status

            elif step_type == "analyze_form":
                 # 형식 분석 로직 구현 (Music21 또는 다른 라이브러리 사용)
                 if isinstance(music_data_representation, stream.Stream):
                      print("워커: 형식 분석 시작 (Music21/다른 기법 예시)...")
                      step_status = "processing"
                      try:
                           # Music21의 분석 모듈 또는 커스텀 로직 사용
                           # 예: 반복 구조, 주제 악구 등을 찾는 로직
                           # form_structure = analysis.form.FormAnalysis(music_data_representation).analyze()
                           form_sections = [{"label": "A", "start": 0, "end": 16}, {"label": "B", "start": 16, "end": 32}] # Mock 결과

                           print(f"워커: 형식 분석 완료 (예시). {len(form_sections)}개 섹션 식별.")
                           processed_results["form_analysis"] = {
                               "status": "success",
                               "sections": form_sections
                           }
                           step_status = "success"

                      except Exception as e:
                           print(f"워커: 형식 분석 중 오류 발생: {e}", exc_info=True)
                           step_status = "failed"
                           processed_results[f"{step_type}_error"] = str(e)
                 else:
                      print("워커: Music21 Stream 객체가 없어 형식 분석 건너뜁니다.")
                      step_status = "skipped"
                 processed_results[f"{step_type}_status"] = step_status


            # TODO: 대위법 분석 등 다른 분석 작업 타입 추가


            # ... (나머지 단계 및 final/finally 블록 유지) ...

# ... (process_task 함수의 반환 부분 유지) ...
                
                elif step_type == "generate_music_file":
                    output_format = step.get("output_format", "midi").lower()
                    if "music_data_extraction" in processed_results and music_data_representation:
                         print(f"워커: 음악 파일 ({output_format}) 생성 시작...")
                         generated_file_path = None
                         # TODO: 음악 데이터 (music_data_representation)를 기반으로 MIDI/MP3 파일 생성
                         # 예: generated_file_path = generate_audio(music_data_representation, output_format)

                         try:
                             if output_format == "midi":
                                 generated_file_path = f"/tmp/{task_id}.mid"
                                 # music_data_representation.write('midi', fp=generated_file_path) # music21 예시
                                 with open(generated_file_path, 'wb') as f: f.write(b"MIDI_DATA_MOCK") # Mock 파일 생성
                                 print("워커: MIDI 파일 생성 완료 (예시).")

                             elif output_format == "mp3":
                                  generated_file_path = f"/tmp/{task_id}.mp3"
                                  # TODO: MIDI -> 오디오 렌더링 -> MP3 인코딩 로직
                                  with open(generated_file_path, 'wb') as f: f.write(b"MP3_DATA_MOCK") # Mock 파일 생성
                                  print("워커: MP3 파일 생성 완료 (예시).")

                             else:
                                 print(f"워커: 지원하지 않는 음악 출력 형식 ({output_format}).")
                                 raise ValueError("Unsupported music output format")

                             if generated_file_path and os.path.exists(generated_file_path):
                                 # 생성된 파일을 결과 스토리지에 업로드
                                 result_s3_key = f"results/{task_id}/{os.path.basename(generated_file_path)}"
                                 print(f"워커: 생성된 결과 파일 S3 업로드 시도: {result_s3_key}")
                                 # TODO: upload_local_file_to_s3 함수 호출
                                 s3_client = boto3.client('s3')
                                 s3_client.upload_file(generated_file_path, STORAGE_CONFIG["bucket_name"], result_s3_key)
                                 print("워커: 결과 파일 S3 업로드 완료 (예시).")
                                 processed_results["generated_music_file"] = {
                                    "status": "success",
                                    "format": output_format,
                                    "s3_key": result_s3_key,
                                    "s3_url": f"s3://{STORAGE_CONFIG['bucket_name']}/{result_s3_key}" # 예시 URL
                                 }
                                 step_success = True
                                 # 임시 파일 삭제
                                 os.remove(generated_file_path)


                         except Exception as e:
                             print(f"워커: 음악 파일 생성 또는 업로드 오류: {e}")
                             processed_results["generated_music_file"] = {"status": "failed", "error": str(e)}
                             # 실패했지만 전체 작업 중단은 아님

                    else:
                        print("워커: 악보 데이터가 없거나 추출 단계 실패로 음악 파일 생성 건너뜁니다.")
                        processed_results["generated_music_file"] = {"status": "skipped", "message": "Music data not available"}
                        step_success = True


                else:
                    # 알 수 없는 작업 단계 타입
                    print(f"워커: 경고: 알 수 없는 작업 단계 타입: {step_type}. 건너뜁니다.")
                    processed_results[f"{step_type}_status"] = "skipped_unknown_type"


                # TODO: 각 단계 성공 여부에 따라 overall_status 업데이트 로직 필요

            except Exception as e:
                print(f"워커: 치명적 오류 발생하여 작업 단계 '{step_type}' 처리 중단: {e}", exc_info=True)
                # 특정 단계에서 복구 불가능한 오류 발생 시 전체 작업 실패 처리
                processed_results[f"{step_type}_status"] = "failed_critical"
                overall_status = "failed"
                break # 오류 발생 시 나머지 단계 건너뛰기

        # --- 3. 최종 상태 업데이트 및 결과 저장 ---
        # 모든 단계 완료 또는 중단 후
        print(f"워커: 최종 상태 업데이트 시도 (Task ID: {task_id})...")
        final_processing_time = time.time() - start_time

        final_result_payload = {
             "task_id": task_id,
             "status": overall_status, # 최종 상태 ("processing", "completed", "failed", "completed_with_errors")
             "processing_time_seconds": final_processing_time,
             "results_summary": processed_results # 각 단계별 결과 및 오류 정보
             # TODO: 결과 파일 S3 URL 등 핵심 정보 상위에 노출
        }

        # TODO: 최종 결과 (final_result_payload)를 데이터베이스에 저장하거나
        # 백엔드에게 API 호출로 통보하는 로직 추가 (task_id를 사용하여 백엔드/DB 업데이트)
        print(f"워커: 최종 결과 저장 (예시): {final_result_payload}")

        return final_result_payload # 워커 실행 환경에 따라 반환값이 사용되거나 무시될 수 있음

    finally:
        # 작업 완료 또는 실패 후 임시 파일 정리
        if downloaded_file_path and os.path.exists(downloaded_file_path) and "/tmp/" in downloaded_file_path: # /tmp 에 다운받은 파일만 삭제
             try:
                 os.remove(downloaded_file_path)
                 print(f"워커: 임시 다운로드 파일 삭제 완료: {downloaded_file_path}")
             except Exception as e:
                 print(f"워커: 임시 파일 삭제 중 오류 발생: {e}")

        # 생성된 임시 결과 파일도 삭제
        # if generated_file_path and os.path.exists(generated_file_path) and "/tmp/" in generated_file_path:
        #      try: os.remove(generated_file_path)
        #      except Exception as e: print(f"워커: 임시 결과 파일 삭제 중 오류: {e}")


# --- 워커 실행 방식에 따른 추가 코드 (이 부분은 그대로 유지) ---

# 예시 1: SQS 큐를 지속적으로 폴링하는 워커
# import sqs_listener # SQS 리스너 라이브러리 사용 예시
# def message_handler(message): ...
# if __name__ == "__main__": ...

# 예시 2: AWS Lambda 핸들러
# def lambda_handler(event, context): ...

# 예시 3: HTTP API 호출을 받는 워커 (FastAPI 등 사용)
# from fastapi import FastAPI, HTTPException
# app = FastAPI()
# @app.post("/process/")
# async def process_item(task_payload: dict): ...

# backend/app/worker.py

import json
import os
import time
import uuid
import boto3 # S3 접근을 위해 워커에서도 boto3 필요

# PDF 텍스트 추출 라이브러리 임포트
from pdfminer.high_level import extract_text as pdf_extract_text

# LangChain 및 OpenAI 라이브러리 임포트
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter

# 음악 처리 라이브러리 임포트 (예시)
from music21 import converter, stream # MusicXML, MIDI 파싱/생성 등
import mido # MIDI 파일 처리
# 오디오 렌더링 및 MP3 인코딩 관련 라이브러리는 더 복잡하며, 외부 도구(ffmpeg 등)가 필요할 수 있습니다.
# 예: from pydub import AudioSegment # 오디오 처리 (ffmpeg 필요)

# .env 파일에서 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# AWS SQS 클라이언트 (메시지 수신/삭제)
sqs_client = boto3.client("sqs")

# AWS S3 클라이언트 (파일 다운로드/업로드)
s3_client = boto3.client("s3")

# SQS 큐 URL 및 스토리지 설정 로드
WORKER_SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
STORAGE_CONFIG = {
    "type": os.getenv("STORAGE_TYPE", "s3"),
    "bucket_name": os.getenv("S3_BUCKET_NAME")
    # OCI 등 다른 스토리지 설정도 여기에 추가
}

if not WORKER_SQS_QUEUE_URL:
    print("경고: SQS_QUEUE_URL 환경 변수가 설정되지 않았습니다. 워커가 메시지를 받지 못합니다.")
if not STORAGE_CONFIG["bucket_name"]:
    print("경고: 스토리지 버킷 이름이 설정되지 않았습니다. 파일 다운로드/업로드가 작동하지 않습니다.")

# OpenAI API 키 설정 (환경 변수 OPENAI_API_KEY 로 설정 권장)
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


def download_file_from_s3(bucket_name: str, object_key: str, local_path: str):
    """S3에서 파일을 로컬 경로로 다운로드합니다."""
    try:
        s3_client.download_file(bucket_name, object_key, local_path)
        print(f"워커: S3 다운로드 성공: {object_key} -> {local_path}")
    except Exception as e:
        print(f"워커: S3 다운로드 오류: {e}")
        raise

def upload_local_file_to_s3(local_path: str, bucket_name: str, object_key: str):
     """로컬 파일을 S3에 업로드합니다."""
     try:
         s3_client.upload_file(local_path, bucket_name, object_key)
         print(f"워커: S3 업로드 성공: {local_path} -> {object_key}")
     except Exception as e:
         print(f"워커: S3 업로드 오류: {e}")
         raise
# backend/app/worker.py (부분 코드)

import subprocess
import sys # 에러 로깅에 필요

# ... (다른 임포트 유지) ...

def run_command(command: list, cwd: str = None, shell: bool = False, env: dict = None):
    """
    외부 명령어를 실행하고 표준 출력/에러를 반환합니다.
    명령어 실행 실패 시 예외를 발생시킵니다.

    :param command: 실행할 명령어와 인자들을 담은 문자열 리스트 (예: ['ls', '-l'])
    :param cwd: 명령어를 실행할 현재 작업 디렉토리 경로
    :param shell: 쉘을 통해 명령어 실행 여부 (보안상 False 권장, 문자열 명령 사용 시 True)
    :param env: 명령어 실행 시 사용할 환경 변수 딕셔너리 (None 시 현재 환경 사용)
    :return: 명령어 실행의 표준 출력 (문자열)
    :raises FileNotFoundError: 실행 파일 경로를 찾을 수 없을 때
    :raises RuntimeError: 명령어 실행 중 0이 아닌 종료 코드가 반환되거나 다른 오류 발생 시
    """
    command_str = " ".join(command) # 로깅을 위해 명령어 문자열 생성
    print(f"워커: 외부 명령어 실행 시작: {command_str}")
    if cwd:
        print(f"워커: 실행 디렉토리: {cwd}")

    try:
        # subprocess.run: 명령어 실행, 완료까지 대기, 결과 반환
        # capture_output=True: 표준 출력과 표준 에러를 캡처
        # text=True: 캡처된 출력/에러를 텍스트로 디코딩 (기본 시스템 인코딩 사용)
        # check=True: 명령어 실행 결과가 0이 아닌 종료 코드를 반환하면 CalledProcessError 예외 발생
        # env: 자식 프로세스에 전달할 환경 변수 딕셔너리 (예: PATH, API 키 등)
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            shell=shell,
            env=env
        )

        print("워커: 명령어 실행 성공.")
        if result.stdout:
            print("워커: stdout:\n", result.stdout.strip()) # 공백 제거하고 출력
        if result.stderr:
            # 표준 에러에 경고나 정보가 담기는 경우도 있으므로 오류가 아니더라도 출력
            print("워커: stderr:\n", result.stderr.strip())

        return result.stdout # 표준 출력 반환

    except FileNotFoundError:
        print(f"워커: 오류: 명령어 실행 파일 '{command[0]}'를 찾을 수 없습니다.", file=sys.stderr) # 표준 에러로 출력
        raise FileNotFoundError(f"Command not found: {command[0]}. Make sure it's installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        # check=True 때문에 0이 아닌 종료 코드 시 이 예외 발생
        error_output = e.stderr.strip() if e.stderr else "No stderr output."
        print(f"워커: 명령어 실행 실패 (종료 코드 {e.returncode}):", file=sys.stderr)
        print("워커: stdout:\n", e.stdout.strip(), file=sys.stderr)
        print("워커: stderr:\n", error_output, file=sys.stderr)
        # 더 구체적인 오류 메시지와 함께 RuntimeError 발생
        raise RuntimeError(f"External command failed with exit code {e.returncode}. Error: {error_output}")
    except Exception as e:
        # 그 외 예상치 못한 예외 처리
        print(f"워커: 예기치 않은 명령어 실행 오류: {e}", file=sys.stderr)
        raise RuntimeError(f"An unexpected error occurred while running command: {e}")

# ... (process_task 함수 및 다른 코드 유지) ...

def process_task(task_payload: dict):
    """
    주어진 작업 페이로드를 처리합니다. (메시지 큐에서 받은 메시지 본문)
    """
    task_id = task_payload.get("task_id", "unknown-task")
    print(f"\n>>> 워커: 작업 처리 시작 (Task ID: {task_id})")
    start_time = time.time()

    file_location = task_payload.get("file_location")
    processing_steps = task_payload.get("processing_steps", [])
    analysis_tasks = task_payload.get("analysis_tasks", [])
    metadata = task_payload.get("metadata", {})

    processed_results = {"task_id": task_id, "metadata": metadata}
    overall_status = "processing" # 작업 시작 상태

    downloaded_file_path = None
    music_data_representation = None # Music21 Stream 객체 등
    extracted_text = None

    try:
        # --- 1. 파일 다운로드 ---
        if file_location and "type" in file_location and "key" in file_location:
            file_type = file_location["type"]
            file_key = file_location["key"]
            bucket_name = file_location.get("bucket") or STORAGE_CONFIG["bucket_name"] # 페이로드에 없으면 기본 설정 사용

            if not bucket_name and file_type in ["s3", "oci"]:
                 raise ValueError(f"워커: {file_type.upper()} 파일 위치는 버킷 이름이 필요합니다.")

            print(f"워커: 파일 다운로드 시도: 타입={file_type}, 키={file_key}")
            try:
                downloaded_file_path = f"/tmp/{task_id}_{os.path.basename(file_key)}"
                # 실제 다운로드 로직 호출
                if file_type == "s3":
                    download_file_from_s3(bucket_name, file_key, downloaded_file_path)
                elif file_type == "oci":
                     # TODO: OCI 다운로드 로직 호출 (oci SDK 사용)
                     print("워커: OCI 파일 다운로드 (예시).")
                     # call_oci_download(bucket_name, file_key, downloaded_file_path)
                     pass # OCI SDK 사용 코드 추가
                elif file_type == "onprem":
                     # TODO: 온프레미스 파일 접근/복사 로직 (네트워크 연결 필요)
                     # 예: sh_util.copy(file_key, downloaded_file_path)
                     print("워커: 온프레미스 파일 접근/복사 (예시).")
                     pass # 온프레미스 파일 접근 코드
                     if not os.path.exists(downloaded_file_path): raise FileNotFoundError(f"워커: 온프레미스 파일 찾을 수 없음: {downloaded_file_path}")
                else:
                     raise ValueError(f"워커: 지원하지 않는 파일 위치 타입: {file_type}")

                if not os.path.exists(downloaded_file_path):
                     raise RuntimeError("워커: 파일 다운로드 또는 접근 실패.")

                processed_results["downloaded_file"] = {"status": "success", "path": downloaded_file_path, "type": file_type}

            except Exception as e:
                print(f"워커: 파일 다운로드 중 오류 발생: {e}")
                processed_results["download_error"] = str(e)
                overall_status = "failed"
                raise e # 치명적 오류로 간주하여 작업 중단

        else:
            print("워커: 작업 페이로드에 파일 위치 정보가 없습니다.")
            processed_results["download_error"] = "Missing file location in payload"
            overall_status = "failed"
            raise ValueError("Missing file location")


        # --- 2. 처리 단계 실행 (processing_steps + analysis_tasks) ---
        # 모든 단계를 순서대로 실행합니다.
        # backend/app/worker.py (process_task 함수 내부, Music21 관련 부분 상세화)

# ... (앞부분 정의 유지) ...

        # --- 2. 처리 단계 실행 ---
        # ... (all_tasks 순회 루프 유지) ...

            try:
                if step_type == "extract_music_data":
                    # ... (OMR 또는 MusicXML/MIDI 파싱 로직 유지) ...
                    # Music21 converter.parse() 결과로 music_data_representation 변수에 Music21 Stream 객체가 할당됩니다.
                    # 예: music_data_representation = converter.parse(input_path)


                # --- Music21 객체 다루기 예시 (Music21 Stream 객체가 있다고 가정) ---
                if isinstance(music_data_representation, stream.Stream):
                    print("워커: Music21 Stream 객체 처리 시작...")

                    # 1. 악보 전체 순회 및 기본 정보 접근
                    # .flat: 복잡한 계층 구조를 무시하고 모든 요소를 평면적으로 가져옴
                    # .recurse(): 중첩된 스트림을 포함하여 모든 요소를 재귀적으로 순회
                    # for element in music_data_representation.flat:
                    # for element in music_data_representation.recurse():
                    #     print(f"  요소: {element.classes}, 오프셋: {element.offset}") # 요소의 클래스 타입과 시간적 위치 확인

                    # 2. 특정 타입의 요소 찾기
                    # .getElementsByClass(): 특정 클래스 타입의 요소들만 가져옴
                    notes_and_chords = music_data_representation.flat.getElementsByClass(['Note', 'Chord'])
                    print(f"워커: 추출된 음표 및 화음 개수: {len(notes_and_chords)}")

                    lyrics = music_data_representation.flat.getElementsByClass('Lyric')
                    print(f"워커: 추출된 가사 요소 개수: {len(lyrics)}")

                    tempos = music_data_representation.flat.getElementsByClass('TempoIndication')
                    print(f"워커: 추출된 빠르기말 개수: {len(tempos)}")

                    # 마디(Measure) 단위로 접근
                    # measures = music_data_representation.getElementsByClass('Measure')
                    # print(f"워커: 악보의 마디 개수: {len(measures)}")
                    # for measure in measures:
                    #      print(f"  마디 {measure.number}의 요소 개수: {len(measure.elements)}")

                    # 3. 음표 (Note) 객체 정보 접근
                    # for nc in notes_and_chords:
                    #     if isinstance(nc, note.Note):
                    #         print(f"  음표: {nc.pitch.unicodeName} ({nc.pitch.frequency:.2f} Hz), 길이: {nc.duration.quarterLength} 사분음표 길이")
                    #     elif isinstance(nc, chord.Chord):
                    #         print(f"  화음: {nc.pitchedCommonNames}, 길이: {nc.duration.quarterLength} 사분음표 길이")
                    #         # for p in nc.pitches: print(f"    - 음: {p.unicodeName}")

                    # 4. 가사 (Lyric) 객체 정보 접근
                    # extracted_text_content = "" # 번역 단계에서 사용될 텍스트
                    # for ly in lyrics:
                    #      print(f"  가사: {ly.text} (연번: {ly.number}, 원천: {ly. syllabic})")
                    #      extracted_text_content += ly.text + "\n"


                    # 5. 악보 변환 및 조작 (예시)
                    # 조성(Key) 바꾸기 (조옮김 - Transpose)
                    # original_key = music_data_representation.analyze('key') # 조성 분석
                    # interval_to_transpose = interval.Interval('P4') # 완전 4도 위로 올리기
                    # transposed_score = music_data_representation.transpose(interval_to_transpose)
                    # print(f"워커: 악보를 {interval_to_transpose. अर्धfString}만큼 조옮김했습니다.")

                    # 빠르기(Tempo) 바꾸기
                    # for mt in music_data_representation.recurse().getElementsByClass('MetronomeMark'):
                    #      mt.number = 120 # 모든 빠르기를 120으로 설정


                    # 6. Music21 객체 -> MIDI 파일로 쓰기
                    # music_data_representation.write('midi', fp=midi_output_path) # MIDI 파일 생성 코드 (generate_music_file 단계에서 사용)


                    # 7. Music21 객체 -> MusicXML 파일로 쓰기 (디버깅이나 중간 결과 저장 시 유용)
                    # music_data_representation.write('musicxml', fp="/tmp/parsed_score.musicxml")


                    # 8. 간단한 음악 이론 분석 (music21 내장 기능)
                    # chords = music_data_representation.flat.getElementsByClass('Chord')
                    # for ch in chords:
                    #      try:
                    #          # 화음의 근음(Root), 형태(Quality) 분석
                    #          root_pitch = ch.root()
                    #          quality = ch.quality()
                    #          print(f"  화음 ({ch.pitchedCommonNames}): 근음 {root_pitch.name}, 형태 {quality}")
                    #      except:
                    #          pass # 분석 불가능한 화음 건너뛰기


                    print("워커: Music21 Stream 객체 처리 완료.")

                # elif isinstance(music_data_representation, mido.MidiFile):
                #     print("워커: Mido MidiFile 객체 처리 시작...")
                #     # Mido 객체 다루는 코드 (MIDI 메시지 순회 등)
                #     # for msg in music_data_representation.play(): # 메시지 재생
                #     #     print(msg)
                #     # Mido 객체 -> MIDI 파일 쓰기: music_data_representation.save(midi_output_path)
                #     print("워커: Mido MidiFile 객체 처리 완료.")

                # elif isinstance(music_data_representation, dict) and "format" in music_data_representation and music_data_representation["format"] == "MusicXML_JSON":
                #     print("워커: OMR JSON 결과 처리 시작...")
                #     # OMR JSON 결과 구조에 맞게 파싱하고 음악 데이터 추출 로직 구현
                #     print("워커: OMR JSON 결과 처리 완료.")


                # ... (OMR 또는 파싱 결과에 따른 music_data_representation 객체 처리 로직 추가) ...


                # ... (extract_text_from_score 단계 유지 및 상세화) ...
                # Music21 객체에서 추출된 extracted_text_content 변수를 translate_to_shakespearean 단계로 전달


                # ... (translate_to_shakespearean 단계 유지 및 상세화) ...


                # ... (generate_music_file 단계 유지 및 상세화) ...
                # music_data_representation (Music21 또는 Mido 객체)에서 MIDI/MP3 파일 생성 로직 구현

            # ... (나머지 단계 및 final/finally 블록 유지) ...

# --- SQS 메시지 리스닝 및 처리 루프 유지 ---
# ... start_sqs_worker 함수 등 ...
        all_tasks = processing_steps + analysis_tasks

        for step in all_tasks:
            step_type = step.get("type")
            print(f"워커: 작업 단계 '{step_type}' 실행 시도...")
            step_status = "processing" # 단계별 상태
        
            try:
                if step_type == "extract_music_data":
                    if downloaded_file_path:
                        print("워커: 악보 데이터 추출 (OMR/파싱) 시작...")
                        try:
                            file_extension = os.path.splitext(downloaded_file_path)[1].lower()
                            if file_extension in ['.png', '.jpg', '.jpeg', '.pdf']:
                                # OMR 처리 (가장 복잡한 부분)
                                print("워커: 이미지 악보 OMR 처리 (예시)...")
                                # TODO: OMR 라이브러리/서비스 호출. 결과는 music_data_representation에 저장.
                                # 예: music_data_representation = call_omr_service(downloaded_file_path)
                                # OMR 결과에서 텍스트 요소도 함께 추출될 수 있습니다.
                                music_data_representation = {"notes_data": "mock_omr_result", "text_elements": ["Mock Lyric 1", "Mock Note"]} # Mock 결과
                                print("워커: OMR 처리 완료 (예시).")

                            elif file_extension in ['.musicxml', '.mxl']:
                                # MusicXML 파싱
                                print("워커: MusicXML 파싱 시도 (music21 예시)...")
                                # TODO: music21 사용하여 MusicXML 파싱
                                music_data_representation = converter.parse(downloaded_file_path) # Music21 객체
                                print("워커: MusicXML 파싱 완료 (music21 예시).")

                            elif file_extension == '.mid':
                                # MIDI 파일 읽기
                                print("워커: MIDI 파일 읽기 시도 (music21/mido 예시)...")
                                # TODO: music21 또는 mido 사용하여 MIDI 파싱
                                music_data_representation = mido.MidiFile(downloaded_file_path) # mido 객체
                                print("워커: MIDI 파일 읽기 완료 (mido 예시).")

                            else:
                                raise ValueError(f"워커: 지원하지 않는 악보 파일 확장자 ({file_extension})")

                            if music_data_representation:
                                step_status = "success"
                            else:
                                raise RuntimeError("워커: 악보 데이터 추출 실패.")

                        except Exception as e:
                             print(f"워커: 악보 데이터 추출 오류: {e}")
                             step_status = "failed"
                             processed_results[f"{step_type}_error"] = str(e)

                    else:
                        print("워커: 다운로드된 파일이 없어 악보 데이터 추출 건너뜁니다.")
                        step_status = "skipped"


                elif step_type == "extract_text_from_score":
                     # 악보 데이터에서 텍스트 추출
                     if music_data_representation:
                          print("워커: 악보 데이터에서 텍스트 추출 시작...")
                          try:
                              # TODO: music_data_representation에서 가사, 지시어 등 텍스트 요소 추출 로직 구현
                              # 예: extracted_text = extract_text_from_music_data_object(music_data_representation)
                              # music21 예시: score.flat.getElementsByClass('Lyric') 등
                              if isinstance(music_data_representation, stream.Stream): # music21 Stream 객체인 경우
                                   lyrics = music_data_representation.flat.getElementsByClass('Lyric')
                                   extracted_text_list = [l.text for l in lyrics]
                                   # 다른 텍스트 요소(TextExpression 등)도 추출 가능
                                   extracted_text = "\n".join(extracted_text_list)
                              elif isinstance(music_data_representation, dict) and "text_elements" in music_data_representation: # OMR mock 결과인 경우
                                   extracted_text = "\n".join(music_data_representation["text_elements"])
                              else:
                                   extracted_text = "악보 데이터 형식에서 텍스트 추출 방법을 모릅니다."
                                   print("워커: 악보 데이터 형식에서 텍스트 추출 방법 모름.")

                              if extracted_text.strip():
                                  print(f"워커: 텍스트 추출 완료. 길이: {len(extracted_text)}")
                                  step_status = "success"
                                  processed_results["extracted_text_content"] = extracted_text # 추출된 텍스트 내용 저장
                              else:
                                  print("워커: 추출된 텍스트가 없습니다.")
                                  step_status = "success" # 텍스트가 없는 것도 성공으로 간주 가능

                          except Exception as e:
                             print(f"워커: 텍스트 추출 오류: {e}")
                             step_status = "failed"
                             processed_results[f"{step_type}_error"] = str(e)
                             extracted_text = None # 오류 발생 시 추출된 텍스트 초기화

                     else:
                          print("워커: 악보 데이터가 없어 텍스트 추출 건너뜁니다.")
                          step_status = "skipped"


                elif step_type == "translate_to_shakespearean":
                    # 셰익스피어 문체 번역 (LangChain/GPT 사용)
                    text_to_translate = processed_results.get("extracted_text_content") # 이전 단계에서 추출된 텍스트 사용

                    if text_to_translate and text_to_translate.strip():
                        print("워커: 셰익스피어 문체 번역 시작...")
                        # --- LangChain/GPT 번역 코드 (위에서 설명한 내용) ---
                        prompt_template = """Translate the following text into English,
                        and then rewrite the translated text in the style of William Shakespeare.

                        Original Text:
                        "{original_text}"

                        Shakespearean Style Translation:"""

                        PROMPT = PromptTemplate(
                            input_variables=["original_text"],
                            template=prompt_template
                        )
                        llm = ChatOpenAI(model=task_payload.get("model", "gpt-3.5-turbo"), temperature=0.7)
                        chain = LLMChain(llm=llm, prompt=PROMPT)

                        try:
                            # 실제 구현 시 토큰 제한 고려 분할 처리 필수!
                            # 간단히 앞부분만 사용하는 예시
                            text_to_process_for_gpt = text_to_translate
                            if len(text_to_process_for_gpt) > 3000:
                                 text_to_process_for_gpt = text_to_process_for_gpt[:3000] + "..."
                                 print("워커: 텍스트가 길어 앞부분만 사용하여 번역 (제한적)")


                            shakespearean_text = chain.run(original_text=text_to_process_for_gpt)

                            processed_results["shakespearean_translation"] = {
                               "status": "success",
                               "original": text_to_process_for_gpt,
                               "translated": shakespearean_text.strip()
                            }
                            print("워커: 셰익스피어 문체 번역 완료.")
                            step_status = "success"

                        except Exception as e:
                            print(f"워커: 셰익스피어 문체 번역 오류 (LangChain/GPT): {e}")
                            step_status = "failed"
                            processed_results["shakespearean_translation"] = {"status": "failed", "error": str(e)}

                    else:
                        print("워커: 번역할 텍스트가 없어 셰익스피어 문체 번역 건너뜁니다.")
                        step_status = "skipped"
                        processed_results["shakespearean_translation"] = {"status": "skipped", "message": "No text found for translation"}


                elif step_type == "generate_music_file":
                    output_format = step.get("output_format", "midi").lower()
                    if music_data_representation:
                         print(f"워커: 음악 파일 ({output_format}) 생성 시작...")
                         generated_file_path = None

                         try:
                             if output_format == "midi":
                                 print("워커: MIDI 파일 생성 (music21/mido 예시)...")
                                 # TODO: music_data_representation (Music21 or mido object) -> MIDI 파일
                                 generated_file_path = f"/tmp/{task_id}.mid"
                                 if isinstance(music_data_representation, stream.Stream): # music21
                                     music_data_representation.write('midi', fp=generated_file_path)
                                 elif isinstance(music_data_representation, mido.MidiFile): # mido
                                      music_data_representation.save(generated_file_path)
                                 else:
                                     raise TypeError("워커: MIDI 생성을 지원하지 않는 음악 데이터 형식.")

                                 print(f"워커: MIDI 파일 생성 완료: {generated_file_path}")


                             elif output_format == "mp3":
                                  print("워커: MP3 파일 생성 (MIDI -> 오디오 렌더링 예시)...")
                                  # TODO: MIDI 데이터 (music_data_representation 또는 중간 MIDI 파일) -> 오디오 렌더링 -> MP3 인코딩
                                  # 이 과정은 신디사이저(fluidsynth) 호출 및 인코딩(ffmpeg) 등 외부 도구 연동이 필요할 수 있습니다.
                                  # 예: raw_audio_path = synthesize_midi_to_wav(midi_data_source)
                                  # 예: mp3_file_path = encode_wav_to_mp3(raw_audio_path)
                                  generated_file_path = f"/tmp/{task_id}.mp3"
                                  # Mock 파일 생성
                                  with open(generated_file_path, 'wb') as f: f.write(b"MP3_DATA_MOCK")
                                  print(f"워커: MP3 파일 생성 완료 (예시): {generated_file_path}")

                             else:
                                 raise ValueError(f"워커: 지원하지 않는 음악 출력 형식 ({output_format}).")


                             if generated_file_path and os.path.exists(generated_file_path):
                                 # 생성된 파일을 결과 스토리지에 업로드
                                 result_s3_key = f"results/{task_id}/{os.path.basename(generated_file_path)}"
                                 print(f"워커: 생성된 결과 파일 S3 업로드 시도: {result_s3_key}")
                                 # TODO: upload_local_file_to_s3 함수 호출
                                 upload_local_file_to_s3(generated_file_path, STORAGE_CONFIG["bucket_name"], result_s3_key)

                                 processed_results["generated_music_file"] = {
                                    "status": "success",
                                    "format": output_format,
                                    "s3_key": result_s3_key,
                                    "s3_url": f"s3://{STORAGE_CONFIG['bucket_name']}/{result_s3_key}" # 예시 URL
                                 }
                                 step_status = "success"
                                 # 임시 파일 삭제
                                 os.remove(generated_file_path)


                             else:
                                 raise RuntimeError("워커: 음악 파일 생성 실패 또는 경로 오류.")


                         except Exception as e:
                             print(f"워커: 음악 파일 생성 또는 업로드 오류: {e}")
                             step_status = "failed"
                             processed_results["generated_music_file"] = {"status": "failed", "error": str(e)}

                    else:
                        print("워커: 악보 데이터가 없어 음악 파일 생성 건너뜁니다.")
                        step_status = "skipped"
                        processed_results["generated_music_file"] = {"status": "skipped", "message": "Music data not available"}


                # TODO: 다른 작업 타입 추가 (예: 음악 스타일 변환, 악기 변경 등)


                else:
                    # 알 수 없는 작업 단계 타입
                    print(f"워커: 경고: 알 수 없는 작업 단계 타입: {step_type}. 건너뜁니다.")
                    step_status = "skipped_unknown_type"
                    processed_results[f"{step_type}_status"] = "skipped_unknown_type"

                # 단계별 최종 상태 기록
                if step_status != "processing":
                     processed_results[f"{step_type}_status"] = step_status

            except Exception as e:
                print(f"워커: 치명적 오류 발생하여 작업 단계 '{step_type}' 처리 중단: {e}", exc_info=True)
                # 특정 단계에서 복구 불가능한 오류 발생 시 전체 작업 실패 처리
                processed_results[f"{step_type}_status"] = "failed_critical"
                overall_status = "failed"
                break # 오류 발생 시 나머지 단계 건너뛰기


        # --- 3. 최종 상태 업데이트 및 결과 저장 ---
        # 모든 단계 완료 또는 중단 후
        if overall_status != "failed": # 치명적 오류가 아니었다면
             overall_status = "completed"
             # 모든 필수 단계가 성공했는지 확인하는 로직 추가 가능
             # 예: if processed_results.get("generate_music_file", {}).get("status") != "success": overall_status = "completed_with_errors"

        final_processing_time = time.time() - start_time

        final_result_payload = {
             "task_id": task_id,
             "status": overall_status, # 최종 상태
             "processing_time_seconds": final_processing_time,
             "results_summary": processed_results # 각 단계별 결과 및 오류 정보
             # TODO: 결과 파일 S3 URL 등 핵심 정보 상위에 노출
        }

        # TODO: 최종 결과 (final_result_payload)를 데이터베이스에 저장하거나
        # 백엔드에게 API 호출로 통보하는 로직 추가 (task_id를 사용하여 백엔드/DB 업데이트)
        # 예: db_service.save_task_result(final_result_payload)
        print(f"워커: 최종 결과 보고 (예시): {final_result_payload}")

        # 작업 성공 시 SQS 메시지 삭제
        # 이 부분은 SQS 리스닝 로직 외부에, 메시지 핸들러에서 process_task 호출 후 처리됩니다.
        # 예: process_task(message_body) 호출 성공 시 message.delete() 호출

        return final_result_payload # 워커 실행 환경에 따라 반환값이 사용되거나 무시될 수 있음

    except Exception as e:
        # 파일 다운로드 또는 초기 단계 오류 등 치명적 오류 처리
        print(f"워커: 작업 '{task_id}' 처리 중 치명적 오류 발생: {e}", exc_info=True)
        final_processing_time = time.time() - start_time
        final_result_payload = {
             "task_id": task_id,
             "status": "failed", # 전체 작업 실패
             "processing_time_seconds": final_processing_time,
             "error_details": str(e),
             "results_summary": processed_results # 실패 시점까지의 결과
        }
        # TODO: 실패 결과 데이터베이스 저장 또는 보고 로직 추가
        print(f"워커: 작업 실패 결과 보고 (예시): {final_result_payload}")
        # 실패 시 SQS 메시지 삭제 안 함 (가시성 제한 시간 후 재처리 시도)

        raise # 예외를 다시 발생시켜 SQS 리스너가 메시지 처리에 실패했음을 알림
    # worker.py (extract_text_from_score 부분 상세화)

# ... (앞부분 임포트 및 process_task 함수 정의 유지) ...

        elif step_type == "extract_text_from_score":
             print("워커: 악보 데이터에서 텍스트 추출 시작...")
             extracted_text = ""
             text_elements_with_info = [] # 텍스트와 위치/타입 정보를 함께 저장할 리스트 (선택 사항)

             if "music_data" in processed_results and music_data_representation is not None:
                  try:
                       # 악보 데이터 표현 방식에 따라 다른 추출 로직 적용
                       if isinstance(music_data_representation, stream.Stream): # music21 Stream 객체인 경우
                            print("워커: Music21 Stream 객체에서 텍스트 요소 추출 시도...")
                            all_elements = music_data_representation.flat.elements # 모든 요소를 평면화하여 가져옴

                            # 추출할 수 있는 텍스트 관련 Music21 클래스들
                            text_classes = [
                                'Lyric', 'TextExpression', 'NoteExpression',
                                'Direction', 'PartLyric', 'ScoreGroup' # ScoreGroup 등에도 텍스트 설명이 있을 수 있음
                                # 필요에 따라 다른 클래스 추가
                            ]

                            for element in all_elements:
                                 # issubclass를 사용하여 상속 관계의 클래스도 포함하여 확인
                                 if any(issubclass(type(element), getattr(__import__('music21'), cls_name)) for cls_name in text_classes):
                                      # 텍스트 속성이 있는지 확인하고 추출
                                      text_content = ""
                                      if hasattr(element, 'text'): # Lyric, TextExpression 등
                                           text_content = element.text
                                      elif hasattr(element, 'content'): # ScoreGroup 등
                                           text_content = element.content
                                      elif hasattr(element, 'value') and hasattr(element.value, 'content'): # Direction with Words
                                           text_content = element.value.content
                                      # TODO: 다른 텍스트 포함 속성 확인 및 추출 로직 추가

                                      if text_content and text_content.strip():
                                           extracted_text += text_content.strip() + "\n"
                                           text_elements_with_info.append({
                                               "type": type(element).__name__, # 요소 클래스 이름
                                               "content": text_content.strip(),
                                               "offset": getattr(element, 'offset', None), # 악보 내 시간적 위치
                                               # "measure_number": element.measureNumber # 마디 번호 (music21 객체 구조에 따라 다름)
                                           })

                            print(f"워커: Music21에서 텍스트 추출 완료. 총 {len(text_elements_with_info)}개 요소.")

                       elif isinstance(music_data_representation, mido.MidiFile): # mido MidiFile 객체인 경우
                           print("워커: Mido MidiFile 객체에서 텍스트 요소 추출 시도...")
                           # MIDI 파일은 기본적으로 악보 텍스트를 표현하기 위한 형식이 아니지만,
                           # 텍스트 이벤트(TextEvent)나 마커(Marker)를 포함할 수 있습니다.
                           extracted_text_list = []
                           for i, track in enumerate(music_data_representation.tracks):
                                for msg in track:
                                     if msg.type in ['text', 'lyrics', 'marker', 'cuepoint', 'copyright']:
                                          extracted_text_list.append(f"Track {i}: [{msg.time}] {msg.text}")
                           extracted_text = "\n".join(extracted_text_list)
                           text_elements_with_info = [{"type": "MIDI Text Event", "content": extracted_text}] # 간단히 목록화

                           print(f"워커: Mido에서 텍스트 이벤트 추출 완료. 총 {len(extracted_text_list)}개 이벤트.")


                       elif isinstance(music_data_representation, dict) and "text_elements" in music_data_representation: # OMR Mock 또는 JSON 형태 결과
                           print("워커: OMR 결과(JSON)에서 텍스트 요소 추출 시도...")
                           # OMR 결과 JSON 구조에 따라 다르게 파싱해야 합니다.
                           # 예시: OMR 결과 JSON에 'text_elements'라는 키가 있고, 그 안에 텍스트 목록이 있다고 가정
                           extracted_text_list = [elem.get('content', '') for elem in music_data_representation.get('text_elements', []) if elem.get('content')]
                           extracted_text = "\n".join(extracted_text_list)
                           text_elements_with_info = music_data_representation.get('text_elements', []) # OMR 결과의 텍스트 요소 정보를 그대로 사용

                           print(f"워커: OMR 결과에서 텍스트 추출 완료. 총 {len(extracted_text_list)}개 요소.")

                       else:
                            print("워커: 지원하지 않거나 텍스트 추출 방법을 모르는 악보 데이터 형식입니다.")
                            # 오류로 처리할지, 아니면 텍스트 추출 건너뛰고 진행할지 결정
                            # raise TypeError("Unsupported music data representation for text extraction")


                       if extracted_text.strip():
                           print(f"워커: 텍스트 추출 완료. 추출된 텍스트 길이: {len(extracted_text)}")
                           processed_results["extracted_text_content"] = extracted_text # 번역용 문자열 저장
                           processed_results["extracted_text_elements"] = text_elements_with_info # (선택 사항) 상세 정보 목록 저장
                           step_status = "success"
                       else:
                           print("워커: 악보에서 추출된 텍스트가 없습니다.")
                           step_status = "success" # 텍스트가 없는 것도 정상적인 경우

                  except Exception as e:
                       print(f"워커: 텍스트 추출 중 오류 발생: {e}", exc_info=True)
                       step_status = "failed"
                       processed_results[f"{step_type}_error"] = str(e)
                       extracted_text = None # 오류 발생 시 텍스트 초기화

             else:
                  print("워커: 악보 데이터가 없거나 추출 단계 실패로 텍스트 추출 건너뜁니다.")
                  step_status = "skipped"

             # 단계별 상태 기록
             processed_results[f"{step_type}_status"] = step_status


# ... (process_task 함수의 다음 단계들 유지) ...
# worker.py (translate_to_shakespearean 부분 상세화)

# ... (앞부분 임포트 유지) ...

# 셰익스피어 번역 관련 라이브러리 (LangChain, OpenAI) 및 설정 로드
from langchain_openai import ChatOpenAI # gpt-3.5-turbo에 ChatOpenAI 사용 권장
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter # 긴 텍스트 분할에 더 유연
# API 호출 재시도 라이브러리
from tenacity import retry, stop_after_attempt, wait_exponential # pip install tenacity

# .env에서 OpenAI API 키 로드는 위에 이미 있습니다.
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# LangChain LLM 인스턴스 생성 (이 부분은 함수 외부에 생성하여 재사용 가능)
# 온도(temperature)는 창의성 조절. 0.7 정도면 스타일 변환에 적합
try:
    llm_shakespeare = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"), temperature=0.7)
    # 모델 이름은 환경 변수 등으로 관리하는 것이 좋음
except Exception as e:
    print(f"워커: OpenAI LLM 인스턴스 생성 오류: {e}")
    llm_shakespeare = None # LLM 사용 불가 상태


# 프롬프트 템플릿 정의 (셰익스피어 문체 가이드라인 강화)
# {original_text} 변수에 번역할 텍스트가 들어갑니다.
# 원본 언어 지정, 결과 형식 지정 등 추가 가이드라인 포함.
SHAKESPEARE_PROMPT_TEMPLATE = """Translate the following text into English,
and then rewrite the translated text in the style of William Shakespeare.
Focus on using vocabulary, phrasing, and sentence structures common in the Elizabethan era.
Maintain the original meaning and context as accurately as possible.

Original Text (Language: {original_language}):
"{original_text}"

Shakespearean Style Translation:"""

SHAKESPEARE_PROMPT = PromptTemplate(
    input_variables=["original_text", "original_language"], # 원본 언어 변수 추가
    template=SHAKESPEARE_PROMPT_TEMPLATE
)

# 긴 텍스트 분할 설정
# 재귀적으로 분할 시도. chunk_size와 chunk_overlap 조정
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500, # GPT-3.5-turbo 토큰 제한(약 4000)보다 작게 설정
    chunk_overlap=100, # 청크 간 겹치는 부분 (문맥 유지를 도움)
    length_function=len,
    add_start_index=True, # 분할된 청크의 원본 텍스트 시작 위치 추가
)


# OpenAI API 호출에 대한 재시도 데코레이터
# 3번 시도하고, 실패 시 지수적으로 대기 시간 증가 (최대 10초 대기)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_llm_with_retry(prompt_text: str, llm_chain: LLMChain):
    """LLM 체인을 호출하고 재시도 로직을 적용합니다."""
    print(f"워커: LLM 호출 시도 (프롬프트 시작: {prompt_text[:100]}...)")
    response = llm_chain.run(original_text=prompt_text) # 체인 실행
    print("워커: LLM 호출 성공.")
    return response


# 텍스트 원본 언어 감지 함수 (langdetect 라이브러리 사용 예시)
# pip install langdetect
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

def detect_language(text: str) -> str:
    """텍스트의 원본 언어를 감지합니다."""
    try:
        # 텍스트가 너무 짧으면 감지 오류 발생 가능성 높음
        if len(text) < 10: # 임의의 최소 길이 설정
             return "unknown"
        lang_code = detect(text)
        return lang_code
    except LangDetectException:
        print("워커: 언어 감지 오류 발생.")
        return "unknown"
    except Exception as e:
         print(f"워커: 예기치 않은 언어 감지 오류: {e}")
         return "unknown"


# ... (process_task 함수의 다운로드 및 추출 부분 유지) ...

        elif step_type == "translate_to_shakespearean":
            # 셰익스피어 문체 번역 (LangChain/GPT 사용)
            extracted_text_content = processed_results.get("extracted_text_content") # 이전 단계에서 추출된 텍스트 사용

            if not llm_shakespeare:
                 print("워커: LLM 인스턴스가 없어 셰익스피어 문체 번역 불가. 단계 건너뜁니다.")
                 step_status = "skipped"
                 processed_results["shakespearean_translation"] = {"status": "skipped", "message": "LLM not initialized"}

            elif extracted_text_content and extracted_text_content.strip():
                print("워커: 셰익스피어 문체 번역 시작...")
                translation_results = [] # 각 청크별 번역 결과를 저장할 리스트
                step_status = "processing"

                try:
                    # 1. 원본 텍스트 언어 감지
                    original_language = detect_language(extracted_text_content)
                    print(f"워커: 감지된 원본 언어: {original_language}")
                    processed_results["detected_language"] = original_language

                    # 2. 긴 텍스트를 청크로 분할
                    # LangChain의 create_documents는 파일 로더처럼 작동하지만, 여기서는 문자열을 직접 분할
                    # text_splitter.create_documents([extracted_text_content]) # Document 객체 리스트 반환
                    texts = text_splitter.split_text(extracted_text_content) # 문자열 리스트 반환
                    print(f"워커: 원본 텍스트가 {len(texts)}개의 청크로 분할되었습니다.")


                    # 3. 각 청크별로 LLM 호출 및 번역/변환 수행
                    llm_chain = LLMChain(llm=llm_shakespeare, prompt=SHAKESPEARE_PROMPT)

                    for i, chunk in enumerate(texts):
                        print(f"워커: 청크 {i+1}/{len(texts)} 처리 시작...")
                        try:
                            # LLM 호출 (재시도 데코레이터 적용)
                            shakespearean_text = call_llm_with_retry(
                                prompt_text=chunk, # 청크 텍스트
                                llm_chain=llm_chain # LLM 체인 인스턴스
                            )

                            translation_results.append({
                                "chunk_index": i,
                                "original_chunk": chunk,
                                "translated_chunk": shakespearean_text.strip(),
                                "status": "success"
                            })
                            print(f"워커: 청크 {i+1} 처리 완료.")

                        except Exception as e:
                            print(f"워커: 청크 {i+1} 처리 중 오류 발생: {e}")
                            translation_results.append({
                                "chunk_index": i,
                                "original_chunk": chunk,
                                "translated_chunk": None,
                                "status": "failed",
                                "error": str(e)
                            })
                            # 특정 청크 실패 시 전체 번역을 실패로 간주할지, 부분 결과만 사용할지 결정 필요

                    # 4. 번역된 청크 결과 합치기
                    # 간단히 번역된 청크들을 이어 붙이지만, 문맥상 자연스럽게 합치는 로직은 더 복잡할 수 있음.
                    # 예시: '\n\n'.join([res['translated_chunk'] for res in translation_results if res['status'] == 'success'])
                    # 여기서는 결과 목록 자체를 저장
                    processed_results["shakespearean_translation"] = {
                       "status": "completed", # 모든 청크 처리가 완료되면 completed
                       "original_language": original_language,
                       "chunks_processed": len(texts),
                       "translation_results_per_chunk": translation_results # 각 청크별 결과 목록
                       # 전체 합쳐진 번역 결과 문자열은 필요에 따라 추가 생성
                       # "full_translated_text": "..."
                    }
                    print("워커: 셰익스피어 문체 번역 단계 처리 완료.")
                    # 모든 청크가 성공했는지 확인하여 최종 단계 상태 결정
                    if all(res['status'] == 'success' for res in translation_results):
                         step_status = "success"
                         processed_results["shakespearean_translation"]["status"] = "success"
                    else:
                         step_status = "completed_with_errors" # 일부 청크 실패
                         processed_results["shakespearean_translation"]["status"] = "completed_with_errors"


                except Exception as e:
                    print(f"워커: 셰익스피어 문체 번역 단계 실행 중 오류 발생: {e}", exc_info=True)
                    step_status = "failed"
                    processed_results["shakespearean_translation"] = {"status": "failed", "error": str(e)}


            else:
                print("워커: 번역할 텍스트가 없거나 추출 단계 실패로 셰익스피어 문체 번역 건너뜁니다.")
                step_status = "skipped"
                processed_results["shakespearean_translation"] = {"status": "skipped", "message": "No text found or extracted for translation"}

            # 단계별 최종 상태 기록
            processed_results[f"{step_type}_status"] = step_status

# ... (process_task 함수의 다음 단계들 및 finally 블록 유지) ...

# 이 루프 안에서 메시지를 받아 process_task 함수를 호출합니다.
# ...   


    finally:
        # 작업 완료 또는 실패 후 임시 파일 정리
        if downloaded_file_path and os.path.exists(downloaded_file_path) and "/tmp/" in downloaded_file_path:
             try:
                 os.remove(downloaded_file_path)
                 print(f"워커: 임시 다운로드 파일 삭제 완료: {downloaded_file_path}")
             except Exception as e:
                 print(f"워커: 임시 파일 삭제 중 오류 발생: {e}")

        # 생성된 임시 결과 파일도 삭제 (S3에 업로드 후)
        # if generated_file_path and os.path.exists(generated_file_path) and "/tmp/" in generated_file_path:
        #      try: os.remove(generated_file_path)
        #      except Exception as e: print(f"워커: 임시 결과 파일 삭제 중 오류: {e}")


# --- SQS 메시지 리스닝 및 처리 루프 (워커의 실제 실행 코드) ---

# 이 부분은 워커가 컨테이너 시작 시 실제로 실행될 코드입니다.
# SQS 큐에서 메시지를 지속적으로 받아 process_task 함수를 호출합니다.

def start_sqs_worker():
    """SQS 큐에서 메시지를 받아 작업을 처리하는 워커를 시작합니다."""
    if not WORKER_SQS_QUEUE_URL:
        print("워커 실행 오류: SQS_QUEUE_URL이 설정되지 않았습니다.")
        return

    print(f"워커: SQS 큐 {WORKER_SQS_QUEUE_URL} 리스닝 시작...")

    while True: # 워커 프로세스가 종료되지 않고 계속 실행
        try:
            # SQS 큐에서 메시지 최대 1개(MaxNumberOfMessages=1) 가져오기
            # WaitTimeSeconds=20: Long Polling (메시지가 도착할 때까지 최대 20초 대기)
            response = sqs_client.receive_message(
                QueueUrl=WORKER_SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                VisibilityTimeout=300 # 메시지를 숨기는 시간 (처리 시간보다 길게 설정)
                                      # 이 시간 안에 메시지 삭제 안 하면 다른 워커가 가져갈 수 있음
            )

            messages = response.get('Messages', [])

            if not messages:
                # print("워커: 대기 중...") # 메시지가 없으면 대기
                continue # 메시지가 없으면 다시 큐 폴링

            for message in messages:
                message_body = message['Body']
                receipt_handle = message['ReceiptHandle'] # 메시지 삭제 시 필요

                print(f"\n>>> 워커: 메시지 수신: {message_body[:100]}...") # 메시지 내용 일부 출력

                try:
                    # 메시지 본문(JSON 문자열)을 파싱하여 작업 페이로드 딕셔너리로 변환
                    task_payload = json.loads(message_body)

                    # 실제 작업 처리 함수 호출
                    process_task(task_payload)

                    # 작업 처리 성공 시 SQS 큐에서 메시지 삭제
                    sqs_client.delete_message(
                        QueueUrl=WORKER_SQS_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )
                    print(f"워커: 메시지 삭제 성공 (ReceiptHandle: {receipt_handle[:10]}...).")

                except json.JSONDecodeError:
                    print(f"워커: 오류: 유효하지 않은 JSON 메시지 본문: {message_body}")
                    # 유효하지 않은 메시지는 삭제하거나 DLQ로 보내도록 처리 (여기서는 일단 로그만 남김)
                    # sqs_client.delete_message(...) 또는 DLQ 로직

                except Exception as e:
                    print(f"워커: 작업 처리 중 오류 발생 (메시지 수신 루프): {e}", exc_info=True)
                    # process_task 내부에서 이미 예외를 처리하지만, 혹시 모를 외부 예외 처리
                    # SQS Visibility Timeout이 지나면 메시지는 다시 보이게 되어 재처리될 수 있습니다.
                    # 반복 실패하는 메시지는 DLQ 설정이 필요합니다.

        except ClientError as e:
             print(f"워커: SQS 클라이언트 오류 발생: {e}")
             # SQS 통신 오류 시 잠시 대기 후 재시도
             time.sleep(5)
        except Exception as e:
            print(f"워커: 메시지 수신 루프 중 예기치 않은 오류 발생: {e}", exc_info=True)
            # 다른 오류 발생 시 잠시 대기 후 재시도
            time.sleep(5)


# 워커 컨테이너의 진입점 (Dockerfile 또는 docker-compose.yml의 command에서 이 함수를 호출)
# docker-compose.yml에서 command: python -u app/worker.py 로 설정했다면,
# 이 파일이 실행될 때 아래 __main__ 블록이 실행됩니다.
if __name__ == "__main__":
    # SQS 워커 시작 함수 호출
    start_sqs_worker()
