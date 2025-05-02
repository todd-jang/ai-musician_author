# backend/app/services/s3_service.py

import boto3
import os
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

# AWS S3 클라이언트 생성
# 자격 증명은 환경 변수, ~/.aws/credentials 등에서 자동으로 로드됩니다.
# region_name은 필요에 따라 설정하세요.
s3_client = boto3.client("s3")

def upload_file_to_s3(file_object, bucket_name: str, object_name: str):
    """
    메모리 파일 객체를 지정된 S3 버킷에 업로드합니다.

    :param file_object: 업로드할 파일 객체 (예: UploadFile)
    :param bucket_name: 대상 S3 버킷 이름
    :param object_name: S3에 저장될 객체의 이름 (경로 포함)
    :return: 업로드된 S3 객체의 URL 또는 실패 시 None
    """
    try:
        # file_object는 read() 메소드를 가진 파일과 유사한 객체입니다.
        # UploadFile 객체는 직접 boto3 upload_fileobj에 전달할 수 있습니다.
        s3_client.upload_fileobj(file_object, bucket_name, object_name)

        # 업로드 성공 시 객체 URL 반환 (퍼블릭 접근 가능하도록 설정된 경우)
        # 보안상 Private으로 설정하고 Pre-signed URL을 사용하는 것이 일반적입니다.
        # 여기서는 예시로 기본적인 URL 형식을 사용합니다.
        region = s3_client.meta.region_name
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_name}"
        print(f"파일 '{object_name}'가 S3 '{bucket_name}'에 성공적으로 업로드되었습니다.")
        return s3_url

    except FileNotFoundError:
        print(f"오류: 파일 객체를 찾을 수 없습니다.")
        return None
    except NoCredentialsError:
        print("오류: AWS 자격 증명을 찾을 수 없습니다.")
        print("환경 변수 (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) 또는 ~/.aws/credentials 파일을 확인하세요.")
        return None
    except PartialCredentialsError:
        print("오류: AWS 자격 증명이 불완전합니다.")
        return None
    except ClientError as e:
        # AWS API 호출 중 오류 발생 시
        print(f"S3 클라이언트 오류 발생: {e}")
        return None
    except Exception as e:
        print(f"파일 업로드 중 예기치 않은 오류 발생: {e}")
        return None

# --- 참고: 로컬 파일 경로로 업로드하는 함수 (앞선 설명에 있던 것) ---
# 필요하다면 이 함수도 함께 사용할 수 있습니다.
# def upload_local_file_to_s3(file_path, bucket_name: str, object_name: str):
#     try:
#         s3_client.upload_file(file_path, bucket_name, object_name)
#         region = s3_client.meta.region_name
#         s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_name}"
#         print(f"파일 '{file_path}'가 S3 '{bucket_name}/{object_name}'에 성공적으로 업로드되었습니다.")
#         return s3_url
#     except FileNotFoundError:
#         print(f"오류: 로컬 파일을 찾을 수 없습니다 - {file_path}")
#         return None
#     except (NoCredentialsError, PartialCredentialsError) as e:
#          print(f"AWS 자격 증명 오류: {e}")
#          return None
#     except ClientError as e:
#         print(f"S3 클라이언트 오류 발생: {e}")
#         return None
#     except Exception as e:
#         print(f"로컬 파일 업로드 중 예기치 않은 오류 발생: {e}")
#         return None
