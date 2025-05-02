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
