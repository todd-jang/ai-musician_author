실행 방법:

docker-compose.yml 파일을 위 내용에 맞춰 업데이트하고, localstack/init-aws.sh 파일을 생성합니다.
db/init.sql 파일이 데이터베이스 스키마를 정의하도록 준비합니다.
작은 테스트 악보 파일(test_sheet_music.pdf 등)을 simulate_load.py 스크립트와 같은 디렉토리 또는 스크립트 내 TEST_FILE_PATH에 지정된 경로에 준비합니다.
.env 파일을 생성하고 DB 및 SQS/S3(LocalStack용) 환경 변수를 설정합니다.
코드 스니펫

LOG_LEVEL=INFO
PRIMARY_DB_TYPE=postgresql
POSTGRES_DB=mydatabase
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
# LocalStack SQS/S3 설정 (Backend, Worker에서 사용)
AWS_ENDPOINT_URL=http://localstack:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
SQS_QUEUE_NAME=personal-data-assistant-queue
S3_BUCKET_NAME=my-local-s3-bucket
# 필요한 경우 OMR, FluidSynth 등 외부 도구 관련 환경 변수 설정
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx # 실제 사용 시
(선택 사항) 워커 컨테이너에 OMR, FluidSynth, FFmpeg 등이 설치되어 있거나 mock 스크립트로 대체되어 있는지 확인합니다. LocalStack은 AWS 서비스만 시뮬레이션하며 이러한 외부 도구는 포함하지 않습니다. 시뮬레이션 범위에 따라 외부 도구 호출 부분을 Mock 처리할 수 있습니다.
터미널에서 Docker Compose 파일을 실행하여 시스템을 가동합니다.
Bash

docker compose up --build -d # -d 는 백그라운드로 실행
필요하다면 워커 인스턴스 수를 늘립니다.
Bash

docker compose up --scale worker=5 -d # 워커 5개 인스턴스로 실행
simulate_load.py 스크립트를 실행하여 부하를 발생시킵니다.
Bash

python simulate_load.py --requests 200 --concurrency 20 # 200개 요청, 20개 동시 전송
다른 터미널에서 Docker Compose 로그를 실시간으로 관찰합니다.
Bash

docker compose logs -f
# 특정 서비스 로그만 보려면: docker compose logs -f backend worker
관찰 및 분석:

simulate_load.py 스크립트의 출력: 각 요청의 성공/실패 여부와 걸린 시간을 확인합니다.
Docker Compose 로그:
백엔드 로그: 요청을 받았는지, SQS 메시지 전송에 성공했는지 확인합니다.
LocalStack 로그: SQS 큐에 메시지가 도착했는지, 워커가 메시지를 가져갔는지 확인합니다. SQS 큐 길이 관련 메시지를 찾습니다.
워커 로그: 메시지를 수신했는지, 작업 처리를 시작했는지, 단계별 진행 상황(OMR, Music21, 번역, MP3 생성 등)이 로깅되는지, 작업 완료 또는 실패 로그가 찍히는지 확인합니다. 에러 메시지를 자세히 살펴봅니다.
여러 워커 인스턴스가 동시에 로그를 출력하며 메시지를 처리하는 것을 관찰합니다.
이 시뮬레이션이 드러낼 수 있는 동적 특성 및 잠재적 문제점:

SQS 큐잉 동작: 요청이 처리 속도보다 빠르게 들어올 때 SQS 큐에 메시지가 어떻게 쌓이는지, 워커들이 어떻게 큐에서 메시지를 가져가는지.
워커 부하 분산: 여러 워커 인스턴스에게 작업이 어떻게 분배되는지.
병목 지점: 특정 단계(예: OMR, 음악 합성)가 오래 걸릴 때 다른 작업들에 어떤 영향을 미치는지. 로그에서 특정 단계의 처리 시간이 길게 찍히는 것을 확인할 수 있습니다.
오류 전파 및 처리: 외부 도구 호출 실패, DB 저장 실패 등이 발생했을 때 워커의 오류 처리 로직이 예상대로 작동하는지, 오류 메시지가 로그에 잘 기록되는지.
자원 경합 (제한된 환경에서): Docker Compose 환경의 리소스 한계로 인해 CPU, 메모리 등이 부족해지면서 시스템이 느려지거나 오류가 발생하는지 (실제 클라우드 환경에서는 HPA가 워커 수를 늘려 대응할 수 있습니다).
동시성 문제 (발생 가능성 확인): 드물지만, 여러 워커가 동시에 DB에 접근하거나 공유 리소스에 접근할 때 예상치 못한 문제가 발생하는지 확인합니다 (가능성은 낮지만 복잡한 시스템에서는 발생할 수 있습니다).

------------------------------------------------------
실행 방법:

simulation/ 디렉토리를 만들고 mock_external_service.py와 Dockerfile.mock_openai, requirements.mock_openai.txt 파일을 위 내용으로 생성합니다.
docker-compose.yml 파일을 업데이트하여 mock_openai_service를 추가하고, worker 서비스의 환경 변수(OPENAI_API_BASE)를 설정합니다.
.env 파일에 SIMULATE_DELAY_SECONDS, SIMULATE_ERROR_RATE 등 시뮬레이션 매개변수 환경 변수를 추가하고 원하는 값을 설정합니다.
Docker Compose를 빌드하고 실행합니다.
Bash

docker compose up --build -d
simulate_load.py 스크립트나 다른 방법을 사용하여 워커에게 작업을 지시합니다.
Bash

python simulate_load.py --requests 10 # 번역이 필요한 작업을 지시
docker compose logs -f worker mock_openai_service 명령으로 워커와 Mock 서비스의 로그를 관찰합니다. 워커가 Mock 서비스로 요청을 보내고, Mock 서비스가 설정된 지연/오류 응답을 반환하며, 워커가 이를 어떻게 처리하는지 확인합니다.
이 시뮬레이션의 가치:

이러한 시뮬레이션을 통해 실제 OpenAI API가 느리거나 오류가 발생했을 때 워커가 예상대로 작동하는지, 재시도 로직은 충분한지, 오류가 발생한 작업이 다른 작업의 처리를 방해하지는 않는지 등을 실제 클라우드 환경에 배포하거나 실제 유료 API를 사용하지 않고도 검증할 수 있습니다. Mock 서비스의 매개변수만 변경하면 다양한 시나리오(짧은 지연, 긴 지연, 간헐적 오류, 연속 오류, Rate Limit 등)를 반복적으로 테스트할 수 있습니다.
