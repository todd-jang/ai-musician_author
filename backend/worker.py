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
