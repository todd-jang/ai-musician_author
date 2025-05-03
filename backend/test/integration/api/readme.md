API Gateway는 다음과 같은 중요한 역할을 수행하며, 이 기능들이 백엔드 서비스와 제대로 통합되는지 검증하는 것이 통합 테스트의 핵심입니다.

요청 라우팅 (Routing): API Gateway는 들어오는 외부 요청의 URL 경로와 HTTP 메소드 등을 기반으로 어떤 백엔드 서비스의 어떤 엔드포인트로 요청을 전달할지 결정합니다. 이 라우팅 설정이 정확한지 테스트해야 합니다. (예: /music/upload_sheetmusic 경로의 POST 요청이 백엔드 서비스의 /upload_sheetmusic 엔드포인트로 제대로 전달되는지)
프로토콜 변환 및 연결: 외부에서는 HTTP/HTTPS로 통신하지만, 내부 백엔드 서비스로는 다른 프로토콜이나 내부망 IP/포트로 전달할 수 있습니다. Gateway가 이 변환 및 연결을 제대로 수행하는지 테스트합니다.
인증 및 권한 부여: API Gateway 레벨에서 API 키 검증, JWT 검증 등 사용자 인증이나 기본적인 접근 권한 부여를 처리할 수 있습니다. 이러한 보안 설정이 올바르게 작동하는지 테스트합니다.
요청/응답 변환: 필요에 따라 Gateway에서 요청 헤더나 본문을 수정하거나, 백엔드 응답을 가공하여 클라이언트에 전달할 수 있습니다. 이 변환 로직이 정확한지 테스트합니다.
백엔드와의 연동: API Gateway가 백엔드 서비스에 요청을 전달하고, 백엔드 서비스의 응답을 받아서 클라이언트에게 다시 전달하는 전체 흐름이 정상 작동하는지 테스트합니다. 백엔드 서비스가 Gateway로부터 요청을 올바른 형식으로 받는지도 중요합니다.
API Gateway 통합 테스트 방법:

테스트 실행 위치: 백엔드 서비스가 배포되어 API Gateway를 통해 접근 가능한 상태에서, 시스템 외부 (클라이언트 관점) 또는 테스트 환경 내부의 별도 테스트 러너에서 API Gateway의 외부 공개 엔드포인트로 실제 HTTP 요청을 전송합니다.
테스트 도구: pytest와 httpx 또는 requests 라이브러리를 조합하여 HTTP 요청을 보내고 응답을 검증하는 테스트 코드를 작성할 수 있습니다. 또는 Postman/Newman, k6, JMeter와 같은 API 테스트 또는 부하 테스트 전문 도구를 사용할 수도 있습니다.
검증 내용:
API Gateway의 외부 URL로 요청을 보냈을 때, 백엔드 서비스가 요청을 정상적으로 처리하고 올바른 응답을 반환하는지 확인합니다 (Status Code, Response Body, Headers 등).
Gateway에 설정된 다양한 경로와 HTTP 메소드에 대해 테스트합니다.
Gateway 인증/권한 부여 설정이 유효한 요청은 통과시키고, 유효하지 않은 요청은 차단하거나 오류 응답을 반환하는지 테스트합니다.
잘못된 형식의 요청이나 존재하지 않는 경로에 대한 Gateway의 오류 응답을 테스트합니다.

설명:

테스트 실행 환경: 이 코드는 실제 배포된 NCP API Gateway의 외부 URL로 요청을 보냅니다. 따라서 테스트 실행 환경(별도의 VM, 컨테이너 또는 로컬 환경)에서 배포된 API Gateway 엔드포인트로 네트워크 접속이 가능해야 합니다.
픽스처 (pytest.fixture):
api_gateway_base_url: 테스트 대상 API Gateway의 기본 URL을 환경 변수(API_GATEWAY_BASE_URL)에서 읽어옵니다. 이 환경 변수는 테스트 실행 시 수동 또는 CI/CD 파이프라인에 의해 설정되어야 합니다. URL이 설정되지 않으면 테스트를 건너뜝니다.
http_client: httpx.Client 인스턴스를 생성하여 실제 HTTP 요청을 보냅니다. base_url이 설정되어 있어 상대 경로로 쉽게 요청을 보낼 수 있습니다. scope="session"을 사용하여 모든 테스트 함수가 동일한 클라이언트 인스턴스를 공유하도록 합니다.
테스트 함수 (test_...):
test_upload_sheet_music_via_gateway_success: 악보 파일 업로드 성공 시나리오를 테스트합니다. 가짜 파일 객체(io.BytesIO)와 multipart/form-data 형식으로 요청을 준비하고, http_client.post()를 사용하여 API Gateway의 업로드 엔드포인트로 요청을 보냅니다. 응답 상태 코드(200)와 응답 본문의 구조 및 내용(task_id, status 등)을 검증합니다.
test_upload_sheet_music_invalid_format: 유효하지 않은 파일 형식으로 업로드 시 API Gateway를 통해 예상된 오류 응답(400 Bad Request)을 받는지 테스트합니다.
검증 (assert):
response.status_code == 200: 요청이 성공했는지 확인합니다.
response.json(): 응답 본문을 JSON으로 파싱합니다.
assert "key" in response_data: 응답 본문에 특정 키가 포함되어 있는지 확인합니다.
assert response_data["status"] == "processing_queued": 백엔드가 올바른 상태를 반환했는지 확인합니다.
이 테스트들은 API Gateway가 클라이언트 요청을 받아 백엔드로 올바르게 전달하고, 백엔드의 응답을 다시 클라이언트에게 전달하는 기본적인 통합 흐름을 검증합니다. Gateway에서 처리하는 라우팅, 인증, 변환 등의 설정이 올바르게 적용되었는지 확인하는 데 중요한 테스트입니다.

API Gateway가 시스템의 "hub"로서 핵심적인 역할을 하므로, 이러한 통합 테스트를 통해 Gateway의 안정적인 동작을 확보하는 것이 중요합니다.
