# backend/tests/unit/services/test_s3_service.py

import pytest
import boto3 # Need to import actual boto3 to mock it
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch
import os
import io # To create mock file objects
import tempfile # For creating temporary files/directories
import uuid # For generating unique keys

# Import the service to test
from backend.app.services import s3_service
from backend.app.core import logging_config # Ensure logging is set up for tests

# Set up logging for tests (can be done via a top-level conftest.py fixture or here)
# If not using a conftest.py, call setup_logging here or in a fixture
logging_config.setup_logging()
# Get a logger for this test module
logger = logging.getLogger(__name__)


# --- Pytest Fixtures ---

# Fixture to set the S3 bucket name environment variable for tests
@pytest.fixture(autouse=True) # autouse=True means this fixture runs automatically for all tests
def set_s3_bucket_name():
    original_bucket_name = os.getenv("S3_BUCKET_NAME")
    os.environ["S3_BUCKET_NAME"] = "test-music-score-bucket" # Use a consistent mock bucket name
    yield # Run the test
    # Clean up environment variable after test
    if original_bucket_name is not None:
        os.environ["S3_BUCKET_NAME"] = original_bucket_name
    else:
        del os.environ["S3_BUCKET_NAME"]

# Fixture to mock the boto3 S3 client
@pytest.fixture
def mock_s3_client(mocker):
    # Mock the boto3.client function call specifically for 's3'
    mock_client = MagicMock()
    # When boto3.client('s3') is called, return our mock_client instance
    mocker.patch('boto3.client', return_value=mock_client)

    # Return the mock client instance so tests can configure its methods
    return mock_client


# Fixture to create a temporary local file for download tests
@pytest.fixture
def temp_local_file(tmp_path):
    # tmp_path is a built-in pytest fixture for creating temporary directories
    temp_dir = tmp_path / "downloads"
    temp_dir.mkdir() # Create the downloads directory
    local_file_path = temp_dir / "downloaded_file.test"
    yield local_file_path
    # Clean up the temporary file and directory (pytest's tmp_path handles cleanup automatically)


# --- Unit Tests for upload_file_to_s3 ---

def test_upload_file_to_s3_success(mock_s3_client):
    # Arrange: Define test data
    bucket_name = os.getenv("S3_BUCKET_NAME") # Use the mocked env var
    object_key = f"uploads/{uuid.uuid4()}.pdf"
    # Create a mock file-like object
    mock_file_content = b"mock file content"
    mock_file_object = io.BytesIO(mock_file_content)
    mock_file_object.seek(0) # Ensure file pointer is at the beginning

    # Arrange: Mock the S3 client's upload_fileobj method to indicate success (default return is None)
    mock_s3_client.upload_fileobj.return_value = None # S3 upload_fileobj returns None on success

    # Act: Call the function
    s3_url = s3_service.upload_file_to_s3(mock_file_object, bucket_name, object_key)

    # Assert: Check if upload_fileobj was called with the correct arguments
    mock_s3_client.upload_fileobj.assert_called_once_with(
        mock_file_object, bucket_name, object_key
    )
    # Assert: Check the returned S3 URL format
    # Note: This URL format is an S3 path, not a public HTTP URL.
    # Adjust assertion if the service is expected to generate a different URL type (e.g., pre-signed URL)
    expected_s3_url = f"s3://{bucket_name}/{object_key}"
    assert s3_url == expected_s3_url

    # Clean up the mock file object
    mock_file_object.close()


def test_upload_file_to_s3_failure(mock_s3_client):
    # Arrange: Define test data
    bucket_name = os.getenv("S3_BUCKET_NAME")
    object_key = f"uploads/{uuid.uuid4()}.pdf"
    mock_file_content = b"mock file content"
    mock_file_object = io.BytesIO(mock_file_content)
    mock_file_object.seek(0)

    # Arrange: Mock the S3 client's upload_fileobj method to raise a ClientError
    mock_s3_client.upload_fileobj.side_effect = ClientError(
        {"Error": {"Code": "SomeErrorCode", "Message": "Simulated upload error"}},
        "upload_fileobj" # Operation name
    )

    # Act: Call the function
    s3_url = s3_service.upload_file_to_s3(mock_file_object, bucket_name, object_key)

    # Assert: Check if upload_fileobj was called
    mock_s3_client.upload_fileobj.assert_called_once_with(
        mock_file_object, bucket_name, object_key
    )
    # Assert: Check that the function returned None on failure
    assert s3_url is None

    # Clean up
    mock_file_object.close()


# --- Unit Tests for download_file_from_s3 ---

def test_download_file_from_s3_success(mock_s3_client, temp_local_file):
    # Arrange: Define test data
    bucket_name = os.getenv("S3_BUCKET_NAME")
    object_key = f"results/{uuid.uuid4()}/output.mp3"
    local_file_path = str(temp_local_file) # Get the path from the fixture

    # Arrange: Mock the S3 client's download_file method to indicate success (default return is None)
    mock_s3_client.download_file.return_value = None # S3 download_file returns None on success

    # Act: Call the function
    success = s3_service.download_file_from_s3(bucket_name, object_key, local_file_path)

    # Assert: Check if download_file was called with the correct arguments
    mock_s3_client.download_file.assert_called_once_with(
        bucket_name, object_key, local_file_path
    )
    # Assert: Check that the function returned True
    assert success is True
    # Note: This test doesn't verify the file content, just that the method was called.
    # To verify content, you'd need to mock the file writing process as well, which is more complex.


def test_download_file_from_s3_failure(mock_s3_client, temp_local_file):
    # Arrange: Define test data
    bucket_name = os.getenv("S3_BUCKET_NAME")
    object_key = f"results/{uuid.uuid4()}/output.mp3"
    local_file_path = str(temp_local_file)

    # Arrange: Mock the S3 client's download_file method to raise a ClientError
    mock_s3_client.download_file.side_effect = ClientError(
        {"Error": {"Code": "SomeErrorCode", "Message": "Simulated download error"}},
        "download_file" # Operation name
    )

    # Act: Call the function
    success = s3_service.download_file_from_s3(bucket_name, object_key, local_file_path)

    # Assert: Check if download_file was called
    mock_s3_client.download_file.assert_called_once_with(
        bucket_name, object_key, local_file_path
    )
    # Assert: Check that the function returned False on failure
    assert success is False
    # Assert: Check that the local file was NOT created (or cleaned up if created partially)
    assert not os.path.exists(local_file_path) # s3_service code should clean up on failure


def test_download_file_from_s3_file_not_found(mock_s3_client, temp_local_file):
    # Arrange: Define test data
    bucket_name = os.getenv("S3_BUCKET_NAME")
    object_key = f"results/{uuid.uuid4()}/non_existent_file.mp3"
    local_file_path = str(temp_local_file)

    # Arrange: Mock the S3 client's download_file method to raise a ClientError with 404 code
    mock_s3_client.download_file.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, # Standard S3 404 error code
        "download_file"
    )

    # Act: Call the function
    success = s3_service.download_file_from_s3(bucket_name, object_key, local_file_path)

    # Assert: Check if download_file was called
    mock_s3_client.download_file.assert_called_once_with(
        bucket_name, object_key, local_file_path
    )
    # Assert: Check that the function returned False (file not found is a type of failure)
    assert success is False
    # Assert: Check that the local file was NOT created
    assert not os.path.exists(local_file_path)


# TODO: Add tests for delete_file_from_s3 if implemented
# def test_delete_file_from_s3_success(mock_s3_client): ...
# def test_delete_file_from_s3_failure(mock_s3_client): ...
