# backend/tests/unit/services/test_db_service.py

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import os # For setting environment variables

# Import the actual db_service module
from backend.app.services import db_service
from backend.app.core import logging_config # Ensure logging is set up for tests

# Set up logging for tests
# logging_config.setup_logging() # This might be called globally in pytest fixtures

# --- Pytest Fixtures and Setup ---

# Fixture to set primary DB type for tests
@pytest.fixture(autouse=True) # autouse=True means this fixture runs automatically for all tests
def set_db_type():
    original_db_type = os.getenv("PRIMARY_DB_TYPE")
    os.environ["PRIMARY_DB_TYPE"] = "postgresql" # Test against PostgreSQL implementation
    yield
    # Clean up environment variable after test
    if original_db_type is not None:
        os.environ["PRIMARY_DB_TYPE"] = original_db_type
    else:
        del os.environ["PRIMARY_DB_TYPE"]

# Fixture to mock the database connection pool and connections
# This is the core of isolating db_service from a real DB
@pytest.fixture
def mock_db_pool(mocker):
    # Mock the connection pool class
    mock_pool_class = mocker.patch('psycopg2.pool.SimpleConnectionPool')
    
    # Create a mock pool instance
    mock_pool_instance = MagicMock()
    mock_pool_class.return_value = mock_pool_instance
    
    # Mock the getconn method to return a mock connection
    mock_conn = MagicMock()
    mock_pool_instance.getconn.return_value = mock_conn
    
    # Mock the cursor method to return a mock cursor
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock the execute method of the cursor
    mock_cursor.execute.return_value = None # execute typically returns None
    
    # Mock cursor_factory for DictCursor if used
    # mock_conn.cursor.return_value = MagicMock(rowcount=1) # Add rowcount if needed for UPDATE/DELETE tests
    # mock_conn.cursor_factory = MagicMock(return_value=mock_cursor) # If setting cursor_factory on conn
    
    # Mock the connection and cursor context managers (__enter__ and __exit__)
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False # Don't suppress exceptions
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False # Don't suppress exceptions

    # Mock the putconn method
    mock_pool_instance.putconn.return_value = None

    # Assign the mock pool instance to the global variable in db_service
    # This is necessary because db_service uses a global variable for the pool
    db_service._db_connection_pool = mock_pool_instance

    yield {
        "pool_class": mock_pool_class,
        "pool_instance": mock_pool_instance,
        "conn": mock_conn,
        "cursor": mock_cursor
    }

    # Clean up the global pool variable after the test
    db_service._db_connection_pool = None


# Fixture to mock json.dumps for JSONB fields
@pytest.fixture
def mock_json_dumps(mocker):
    return mocker.patch('json.dumps', side_effect=lambda x: json.dumps(x)) # Use actual json.dumps but mock it


# Fixture to mock datetime.utcnow
@pytest.fixture
def mock_utcnow(mocker):
    mock_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return mocker.patch('db_service.datetime.utcnow', return_value=mock_dt) # Mock utcnow in db_service module


# --- Unit Tests ---

def test_setup_db_connection_pool_success(mocker):
    # Arrange: Mock environment variables and the pool class
    mocker.patch.dict(os.environ, {
        "PRIMARY_DB_TYPE": "postgresql",
        "POSTGRES_DB": "testdb",
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "password",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432"
    })
    mock_pool_class = mocker.patch('psycopg2.pool.SimpleConnectionPool')

    # Act: Call the setup function
    db_service.setup_db_connection_pool(min_conn=2, max_conn=5)

    # Assert: Check if the pool class was called with correct arguments
    mock_pool_class.assert_called_once_with(
        2, 5, database="testdb", user="testuser", password="password", host="localhost", port="5432"
    )
    # Check if the global variable is set
    assert db_service._db_connection_pool is not None


def test_get_db_connection_success(mock_db_pool):
    # Arrange: mock_db_pool fixture handles pool setup and mocks getconn
    # db_service._db_connection_pool is already set by the fixture
    
    # Act: Get a connection
    conn = db_service.get_db_connection()

    # Assert: Check if getconn was called and a connection was returned
    mock_db_pool["pool_instance"].getconn.assert_called_once()
    assert conn is not None
    assert conn == mock_db_pool["conn"] # Ensure the returned connection is the mock connection


def test_release_db_connection_success(mock_db_pool):
    # Arrange: Get a mock connection
    conn = mock_db_pool["conn"]

    # Act: Release the connection
    db_service.release_db_connection(conn)

    # Assert: Check if putconn was called with the correct connection
    mock_db_pool["pool_instance"].putconn.assert_called_once_with(conn)


def test_create_file_entry_success(mock_db_pool, mock_json_dumps):
    # Arrange: Define test data
    file_id = str(uuid.uuid4())
    user_id = 1
    original_filename = "test.pdf"
    file_extension = ".pdf"
    file_size_bytes = 1024
    storage_location = {"type": "s3", "bucket": "mybucket", "key": f"uploads/{file_id}.pdf"}

    # Act: Call the function
    success = db_service.create_file_entry(
        file_id, user_id, original_filename, file_extension, file_size_bytes, storage_location
    )

    # Assert: Check if the correct SQL query was executed with correct parameters
    mock_cursor = mock_db_pool["cursor"]
    mock_cursor.execute.assert_called_once_with(
        """
        INSERT INTO files (file_id, user_id, original_filename, file_extension, file_size_bytes, storage_location)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (file_id, user_id, original_filename, file_extension, file_size_bytes, json.dumps(storage_location))
    )
    # Check if commit was called
    mock_db_pool["conn"].commit.assert_called_once()
    # Check if connection was released
    mock_db_pool["pool_instance"].putconn.assert_called_once_with(mock_db_pool["conn"])
    # Check if the function returned True
    assert success is True


def test_create_task_entry_success(mock_db_pool, mock_json_dumps):
    # Arrange: Define test data
    task_id = str(uuid.uuid4())
    user_id = 1
    file_id = str(uuid.uuid4())
    requested_output_format = "mp3"
    request_shakespearean_translation = True
    requested_analysis_tasks = [{"type": "analyze_harmony"}]

    # Act: Call the function
    success = db_service.create_task_entry(
        task_id, user_id, file_id, requested_output_format, request_shakespearean_translation, requested_analysis_tasks
    )

    # Assert: Check if the correct SQL query was executed with correct parameters
    mock_cursor = mock_db_pool["cursor"]
    mock_cursor.execute.assert_called_once_with(
        """
        INSERT INTO tasks (task_id, user_id, file_id, requested_output_format, request_shakespearean_translation, requested_analysis_tasks)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            task_id,
            user_id,
            file_id,
            requested_output_format,
            request_shakespearean_translation,
            json.dumps(requested_analysis_tasks)
        )
    )
    # Check if commit was called
    mock_db_pool["conn"].commit.assert_called_once()
    # Check if connection was released
    mock_db_pool["pool_instance"].putconn.assert_called_once_with(mock_db_pool["conn"])
    # Check if the function returned True
    assert success is True

# Add more tests for other functions (update_task_status_processing, save_task_result, get_task_status_by_id, get_task_result_details)
# Need to mock cursor.rowcount for update/delete tests
# Need to mock cursor.fetchone() or cursor.fetchall() for select tests and provide mock return values

# Example test for get_task_status_by_id
def test_get_task_status_by_id_found(mock_db_pool):
    # Arrange: Define test data and mock return value for fetchone
    task_id = str(uuid.uuid4())
    mock_return_row = {
        'task_id': task_id,
        'user_id': 1,
        'file_id': str(uuid.uuid4()),
        'requested_output_format': 'mp3',
        'request_shakespearean_translation': True,
        'requested_analysis_tasks': json.dumps([{"type": "analyze_harmony"}]), # JSONB comes as string
        'status': 'completed',
        'created_at': datetime.utcnow(),
        'started_at': datetime.utcnow(),
        'completed_at': datetime.utcnow(),
        'error_message': None
    }
    mock_db_pool["cursor"].fetchone.return_value = mock_return_row
    # Mock cursor.description for DictCursor simulation (needed to get column names)
    mock_db_pool["cursor"].description = [
         ('task_id', None, None, None, None, None, None),
         ('user_id', None, None, None, None, None, None),
         ('file_id', None, None, None, None, None, None),
         ('requested_output_format', None, None, None, None, None, None),
         ('request_shakespearean_translation', None, None, None, None, None, None),
         ('requested_analysis_tasks', None, None, None, None, None, None),
         ('status', None, None, None, None, None, None),
         ('created_at', None, None, None, None, None, None),
         ('started_at', None, None, None, None, None, None),
         ('completed_at', None, None, None, None, None, None),
         ('error_message', None, None, None, None, None, None),
    ]
    # Mock json.loads if you expect the function to parse JSONB strings (DictCursor might do this)
    # mocker.patch('json.loads', side_effect=lambda x: json.loads(x))


    # Act: Call the function
    task_info = db_service.get_task_status_by_id(task_id)

    # Assert: Check if the correct query was executed and the function returned the expected data
    mock_db_pool["cursor"].execute.assert_called_once_with(
        """
        SELECT task_id, user_id, file_id, requested_output_format, request_shakespearean_translation, requested_analysis_tasks, status, created_at, started_at, completed_at, error_message
        FROM tasks
        WHERE task_id = %s
        """,
        (task_id,)
    )
    assert task_info is not None
    assert task_info['task_id'] == task_id
    assert task_info['status'] == 'completed'
    # Note: Testing JSONB parsing might require more sophisticated mocking or integration testing


# Example test for get_task_status_by_id - Not Found case
def test_get_task_status_by_id_not_found(mock_db_pool):
     # Arrange: Mock fetchone to return None (task not found)
     task_id = str(uuid.uuid4())
     mock_db_pool["cursor"].fetchone.return_value = None

     # Mock cursor.description (needed even if no rows are returned for DictCursor)
     mock_db_pool["cursor"].description = []

     # Act: Call the function
     task_info = db_service.get_task_status_by_id(task_id)

     # Assert: Check if the query was executed and the function returned None
     mock_db_pool["cursor"].execute.assert_called_once_with(
         """
         SELECT task_id, user_id, file_id, requested_output_format, request_shakespearean_translation, requested_analysis_tasks, status, created_at, started_at, completed_at, error_message
         FROM tasks
         WHERE task_id = %s
         """,
         (task_id,)
     )
     assert task_info is None

# Add tests for error cases (e.g., DB connection error, query error)
# Use mock_db_pool["pool_instance"].getconn.side_effect = Exception("Connection failed")
# Use mock_db_pool["cursor"].execute.side_effect = Exception("Query failed")
