# backend/tests/integration/api/test_api_gateway.py

import pytest
import httpx # HTTP 클라이언트 라이브러리 (pip install httpx)
import os
import logging
import uuid # 파일명, task_id 생성용

logger = logging.getLogger(__name__)

# --- Test Setup (Conceptual - done OUTSIDE this code file) ---
# 1. Deploy Backend API service to its target environment (e.g., AWS EKS).
# 2. Deploy and Configure NCP API Gateway to route traffic to the Backend API service endpoint.
#    (This configuration is done via infrastructure/terraform/ncp/api_gateway.tf and apply)
# 3. Ensure network connectivity between NCP API Gateway and the Backend API service.
# 4. Obtain the external endpoint URL of the deployed NCP API Gateway.

# --- Pytest Fixtures ---

@pytest.fixture(scope="session") # 세션 범위 픽스처 (테스트 시작 시 한 번만 실행)
def api_gateway_base_url():
    """Fixture to get the base URL of the API Gateway."""
    # API Gateway 외부 URL은 환경 변수 등으로 테스트 실행 환경에 주입되어야 합니다.
    url = os.getenv("API_GATEWAY_BASE_URL")
    if not url:
        pytest.skip("API_GATEWAY_BASE_URL environment variable not set.")
    # URL 끝에 / 가 없도록 보정
    return url.rstrip('/')

@pytest.fixture(scope="session")
def http_client(api_gateway_base_url):
    """Fixture to create an httpx client for making requests."""
    # httpx.Client 는 세션 동안 연결을 재사용하여 효율적입니다.
    client = httpx.Client(base_url=api_gateway_base_url)
    logger.info(f"HTTP client created for API Gateway base URL: {api_gateway_base_url}")
    yield client # 테스트 실행 동안 클라이언트 제공
    client.close() # 테스트 종료 후 클라이언트 닫기

# --- API Gateway Integration Tests ---

def test_upload_sheet_music_via_gateway_success(http_client):
    """
    Tests uploading a sheet music file via the API Gateway.
    This verifies routing and initial processing trigger.
    """
    logger.info("Starting integration test: Uploading sheet music via API Gateway.")

    # Arrange: Prepare a mock file to upload
    test_file_content = b"%PDF-1.0\n% Test PDF content\n" # Simple mock PDF content
    # Use a unique filename to avoid conflicts in storage/tasks
    test_filename = f"test_sheet_{uuid.uuid4()}.pdf"
    files = {'file': (test_filename, io.BytesIO(test_file_content), 'application/pdf')}

    # Arrange: Prepare query parameters for the request
    params = {
        "output_format": "midi",
        "translate_shakespearean": "true" # Query parameters are strings
    }

    # Act: Send the POST request to the API Gateway's upload endpoint
    # The endpoint path must match the API Gateway configuration and the FastAPI router
    upload_endpoint = "/music/upload_sheetmusic"
    logger.info(f"Sending POST request to {http_client.base_url}{upload_endpoint}")
    response = http_client.post(upload_endpoint, files=files, params=params)

    # Assert: Check the response status code
    # Expected: 200 OK from the backend indicating task queued
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}. Response body: {response.text}"

    # Assert: Check the response body structure and content
    # Expected response from backend/app/api/files.py upload_sheet_music endpoint
    response_data = response.json()
    logger.info(f"Received response: {response_data}")

    assert "message" in response_data
    assert "task_id" in response_data
    assert "uploaded_s3_key" in response_data # Or other storage key field
    assert "status" in response_data
    assert response_data["status"] == "processing_queued" # Verify the task was successfully queued

    # Optional: Store task_id for subsequent tests (e.g., status check)
    # pytest-xdist fixture can be used to share data across tests if needed
    pytest.current_task_id = response_data["task_id"]
    logger.info(f"Upload test successful. Task ID: {pytest.current_task_id}")


def test_upload_sheet_music_invalid_format(http_client):
    """Tests uploading a file with an invalid format via the API Gateway."""
    logger.info("Starting integration test: Uploading invalid file format via API Gateway.")

    # Arrange: Prepare a mock file with an invalid extension
    test_file_content = b"invalid file content"
    test_filename = f"test_invalid_{uuid.uuid4()}.txt" # Invalid extension
    files = {'file': (test_filename, io.BytesIO(test_file_content), 'text/plain')}

    # Act: Send the POST request
    upload_endpoint = "/music/upload_sheetmusic"
    response = http_client.post(upload_endpoint, files=files)

    # Assert: Check for a 400 Bad Request from the backend (assuming backend validates format)
    # Or the API Gateway might reject based on content type if configured
    assert response.status_code == 400, f"Expected status code 400, but got {response.status_code}. Response body: {response.text}"
    response_data = response.json()
    assert "detail" in response_data
    assert "Unsupported file format" in response_data["detail"] # Verify the error message


# TODO: Add more API Gateway integration tests
# - Test other endpoints (e.g., status check, assuming it's implemented and routed via Gateway)
# - Test GET requests (if any)
# - Test authentication/authorization (if configured on the Gateway)
# - Test large file uploads (performance/gateway limits)
# - Test error handling when backend is down (Gateway behavior)
