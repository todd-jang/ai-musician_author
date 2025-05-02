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
