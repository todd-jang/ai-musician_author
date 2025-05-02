# backend/app/services/db_service.py

import os
import json
import psycopg2
import psycopg2.pool # For connection pooling
import psycopg2.extras # For DictCursor
# Optional: import cx_Oracle # For Oracle (pip install cx_oracle)
from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime
import uuid # For generating file_id

# --- Configure Logging for this module ---
# Get the logger configured by logging_config.py
logger = logging.getLogger(__name__)

# --- Database Configuration Loading ---
# Load connection details from environment variables
PRIMARY_DB_TYPE = os.getenv("PRIMARY_DB_TYPE", "postgresql").lower() # Default to postgresql

# Configuration dictionary for different DB types
DB_CONFIGS: Dict[str, Dict[str, Any]] = {
    "postgresql": {
        "database": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT", "5432")
    },
    "oracle": {
        "user": os.getenv("ORACLE_USER"),
        "password": os.getenv("ORACLE_PASSWORD"),
        "dsn": os.getenv("ORACLE_DSN") # Oracle connection string
    }
    # TODO: Add config for other DB types if needed (e.g., a separate log DB if it's SQL-based, but typically logs go to Elasticsearch)
}

# --- Database Connection Pooling ---
# Use a global variable for the connection pool instance
# In a real application with dependency injection framework (like FastAPI's Depends),
# manage pool lifecycle and dependency injection more robustly.
_db_connection_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None # Type hint for pool


def setup_db_connection_pool(min_conn: int = 1, max_conn: int = 10):
    """Sets up the database connection pool based on configuration."""
    global _db_connection_pool
    db_type = PRIMARY_DB_TYPE
    config = DB_CONFIGS.get(db_type)

    if not config:
        logger.error(f"Database pool setup failed: No configuration found for type '{db_type}'.")
        return

    # Check if essential config values are present for the chosen DB type
    if db_type == "postgresql":
        if not all(config.get(key) for key in ["database", "user", "password", "host"]):
            logger.error(f"PostgreSQL connection pool setup failed: Incomplete configuration. Config: {config}")
            return
        try:
            # Use SimpleConnectionPool for basic pool
            _db_connection_pool = psycopg2.pool.SimpleConnectionPool(
                min_conn,
                max_conn,
                **config # Pass config dictionary as keyword arguments
            )
            logger.info(f"PostgreSQL connection pool created successfully (min={min_conn}, max={max_conn}).")
        except Exception as e:
            logger.error(f"Error creating PostgreSQL connection pool: {e}", exc_info=True)

    elif db_type == "oracle":
        # TODO: Implement Oracle pool setup using cx_Oracle.SessionPool
        # if cx_Oracle is None:
        #     logger.error("Oracle connection pool setup failed: cx_Oracle library not found.")
        #     return
        # if not all(config.get(key) for key in ["user", "password", "dsn"]):
        #      logger.error("Oracle connection pool setup failed: Incomplete configuration.")
        #      return
        # try:
        #     _db_connection_pool = cx_Oracle.SessionPool(
        #         config["user"], config["password"], config["dsn"], min=min_conn, max=max_conn, increment=1 # Other pool parameters...
        #     )
        #     logger.info(f"Oracle connection pool created successfully (min={min_conn}, max={max_conn}).")
        # except Exception as e:
        #      logger.error(f"Error creating Oracle connection pool: {e}", exc_info=True)
        logger.warning("Oracle connection pool setup not implemented.")
        pass # Placeholder for Oracle

    else:
        logger.error(f"Unsupported database type for connection pool: {db_type}")


def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """Gets a connection from the pool."""
    global _db_connection_pool
    if _db_connection_pool is None:
        # Attempt to set up pool if not already done (basic retry or logging)
        # In a production app, pool should be set up at app startup explicitly
        logger.error("Connection pool is not set up. Call setup_db_connection_pool first.")
        # Optional: try setup_db_connection_pool() again here, but better to fail fast
        return None

    db_type = PRIMARY_DB_TYPE
    try:
        if db_type == "postgresql":
            conn = _db_connection_pool.getconn()
            # Use DictCursor to get results as dictionaries
            # conn.cursor_factory = psycopg2.extras.DictCursor # Set cursor factory if needed for specific queries
            # logger.debug("Got connection from PostgreSQL pool.")
            return conn
        elif db_type == "oracle":
             # TODO: Implement Oracle connection pool acquire
             # if isinstance(_db_connection_pool, cx_Oracle.SessionPool):
             #     conn = _db_connection_pool.acquire()
             #     # logger.debug("Got connection from Oracle pool.")
             #     return conn
             # else:
             #     logger.error("Oracle pool not initialized correctly.")
             #     return None
            logger.warning("Oracle connection acquire not implemented.")
            return None # Placeholder for Oracle
        else:
             logger.error(f"Unsupported database type for getting connection: {db_type}")
             return None

    except Exception as e:
        logger.error(f"Error getting connection from pool ({db_type}): {e}", exc_info=True)
        return None


def release_db_connection(conn: Optional[psycopg2.extensions.connection]):
    """Releases a connection back to the pool."""
    global _db_connection_pool
    if _db_connection_pool is None or conn is None:
        return

    db_type = PRIMARY_DB_TYPE
    try:
        if db_type == "postgresql":
            _db_connection_pool.putconn(conn)
            # logger.debug("Released connection back to PostgreSQL pool.")
        elif db_type == "oracle":
             # TODO: Implement Oracle connection pool release
             # if isinstance(_db_connection_pool, cx_Oracle.SessionPool):
             #     _db_connection_pool.release(conn)
             #     # logger.debug("Released connection back to Oracle pool.")
             # else:
             #     logger.error("Oracle pool not initialized correctly for releasing.")
            logger.warning("Oracle connection release not implemented.")
            pass # Placeholder for Oracle
        else:
             logger.error(f"Unsupported database type for releasing connection: {db_type}")

    except Exception as e:
        logger.error(f"Error releasing connection back to pool ({db_type}): {e}", exc_info=True)


def close_db_connection_pool():
    """Closes the database connection pool."""
    global _db_connection_pool
    if _db_connection_pool is None:
        logger.info("Connection pool is already closed or not set up.")
        return

    db_type = PRIMARY_DB_TYPE
    try:
        if db_type == "postgresql":
            _db_connection_pool.closeall()
            logger.info("PostgreSQL connection pool closed.")
        elif db_type == "oracle":
             # TODO: Implement Oracle connection pool close
             # if isinstance(_db_connection_pool, cx_Oracle.SessionPool):
            #     _db_connection_pool.close()
            #     logger.info("Oracle connection pool closed.")
             # else:
            #      logger.error("Oracle pool not initialized correctly for closing.")
            logger.warning("Oracle connection pool close not implemented.")
            pass # Placeholder for Oracle
        else:
            logger.error(f"Unsupported database type for closing pool: {db_type}")

        _db_connection_pool = None # Set pool to None after closing
    except Exception as e:
        logger.error(f"Error closing connection pool ({db_type}): {e}", exc_info=True)


# --- Database Operation Functions Implementation (PostgreSQL focused) ---

# Helper to execute query and fetch results
def _execute_query(query: str, params: Optional[Tuple] = None, fetchone: bool = False, fetchall: bool = False, commit: bool = False) -> Optional[Any]:
    """Internal helper to get connection, execute query, and handle transaction/release."""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        # Use DictCursor for returning dictionaries
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            logger.debug(f"Executing query: {query[:100]}...", extra={'query': query, 'params': params})
            cur.execute(query, params)

            if commit:
                conn.commit()
                logger.debug("Query committed.")
            
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
            return cur # Return cursor for operations like rowcount if needed

    except Exception as e:
        if conn and not conn.closed: # Check if connection is still open before rollback
             conn.rollback()
             logger.error("Transaction rolled back due to error.", extra={'query': query[:100], 'error': str(e)})
        logger.error(f"Database query failed: {e}", extra={'query': query[:100], 'error': str(e)}, exc_info=True)
        return None
    finally:
        if conn:
            release_db_connection(conn)


# Function to create a new file entry - Called by backend API
def create_file_entry(file_id: str, user_id: Optional[int], original_filename: str, file_extension: str, file_size_bytes: Optional[int], storage_location: Dict[str, Any]) -> bool:
    """Creates a new entry in the files table."""
    if PRIMARY_DB_TYPE != "postgresql": # Only implemented for PostgreSQL
        logger.warning(f"create_file_entry only implemented for PostgreSQL, current type is {PRIMARY_DB_TYPE}")
        return False

    query = """
            INSERT INTO files (file_id, user_id, original_filename, file_extension, file_size_bytes, storage_location)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
    params = (
        file_id,
        user_id,
        original_filename,
        file_extension,
        file_size_bytes,
        json.dumps(storage_location) # JSONB requires string
    )
    result = _execute_query(query, params=params, commit=True)
    if result is not None: # _execute_query returns cursor on success commit
         logger.info(f"File entry created: {file_id}", extra={'file_id': file_id, 'original_filename': original_filename})
         return True
    return False


# Function to create a new task entry - Called by backend API
def create_task_entry(task_id: str, user_id: Optional[int], file_id: str, requested_output_format: str, request_shakespearean_translation: bool, requested_analysis_tasks: Optional[List[Dict[str, Any]]]) -> bool:
    """Creates a new entry in the tasks table."""
    if PRIMARY_DB_TYPE != "postgresql": # Only implemented for PostgreSQL
        logger.warning(f"create_task_entry only implemented for PostgreSQL, current type is {PRIMARY_DB_TYPE}")
        return False

    query = """
            INSERT INTO tasks (task_id, user_id, file_id, requested_output_format, request_shakespearean_translation, requested_analysis_tasks)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
    params = (
        task_id,
        user_id,
        file_id,
        requested_output_format,
        request_shakespearean_translation,
        json.dumps(requested_analysis_tasks) if requested_analysis_tasks is not None else None # JSONB requires string or None
    )
    result = _execute_query(query, params=params, commit=True)
    if result is not None: # _execute_query returns cursor on success commit
        logger.info(f"Task entry created: {task_id}", extra={'task_id': task_id, 'file_id': file_id})
        return True
    return False


# Function to update task status to 'processing' - Called by worker
def update_task_status_processing(task_id: str) -> bool:
    """Updates a task status to 'processing' and sets started_at time."""
    if PRIMARY_DB_TYPE != "postgresql":
         logger.warning(f"update_task_status_processing only implemented for PostgreSQL, current type is {PRIMARY_DB_TYPE}")
         return False

    query = """
            UPDATE tasks
            SET status = %s, started_at = %s
            WHERE task_id = %s AND status = %s
            """
    params = ('processing', datetime.utcnow(), task_id, 'queued')
    result = _execute_query(query, params=params, commit=True)

    if result is not None and result.rowcount > 0: # check rowcount for update success
        logger.info(f"Task status updated to processing: {task_id}", extra={'task_id': task_id, 'status': 'processing'})
        return True
    elif result is not None and result.rowcount == 0:
         logger.warning(f"Task status not updated to processing (not in 'queued' state or not found): {task_id}", extra={'task_id': task_id})
         return False
    return False


# Function to save a task result (completed/failed/errors) - Called by worker
def save_task_result(result_payload: Dict[str, Any]) -> bool:
    """Saves the final task result and updates the task status."""
    if PRIMARY_DB_TYPE != "postgresql":
         logger.warning(f"save_task_result only implemented for PostgreSQL, current type is {PRIMARY_DB_TYPE}")
         return False

    task_id = result_payload.get("task_id")
    if not task_id:
        logger.error("Task result payload is missing task_id.")
        return False

    current_time = datetime.utcnow()
    final_status = result_payload.get("status", "unknown")
    processing_time = result_payload.get("processing_time_seconds")
    error_details = result_payload.get("error_details")
    detailed_results = result_payload.get("results_summary")


    # Use a single transaction for both updates
    conn = get_db_connection()
    if not conn:
        logger.error(f"Failed to get DB connection to save task result: {task_id}", extra={'task_id': task_id})
        return False

    try:
        with conn.cursor() as cur:
            logger.info(f"Saving task result for {task_id} with status: {final_status}", extra={'task_id': task_id, 'status': final_status})

            # Update tasks table status and timestamps
            cur.execute(
                """
                UPDATE tasks
                SET status = %s, completed_at = %s, error_message = %s
                WHERE task_id = %s
                """,
                (final_status, current_time, error_details, task_id)
            )
            logger.debug(f"tasks table updated for result: {task_id}", extra={'task_id': task_id, 'status': final_status})


            # Insert or update task_results table (JSONB requires string)
            cur.execute(
                """
                INSERT INTO task_results (task_id, final_status, processing_time_seconds, detailed_results, completed_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (task_id) DO UPDATE
                SET final_status = EXCLUDED.final_status,
                    processing_time_seconds = EXCLUDED.processing_time_seconds,
                    detailed_results = EXCLUDED.detailed_results,
                    completed_at = EXCLUDED.completed_at;
                """,
                (
                    task_id,
                    final_status,
                    processing_time,
                    json.dumps(detailed_results) if detailed_results is not None else None, # JSONB needs string or None
                    current_time
                )
            )
            logger.debug(f"task_results table inserted/updated: {task_id}", extra={'task_id': task_id})

            conn.commit() # Commit the transaction
            logger.info(f"Task result saved successfully: {task_id}", extra={'task_id': task_id, 'status': final_status})
            return True
    except Exception as e:
        conn.rollback() # Rollback on error
        logger.error(f"Error saving task result for {task_id}: {e}", extra={'task_id': task_id, 'error': str(e), 'status': final_status}, exc_info=True)
        return False
    finally:
        release_db_connection(conn)


# Function to get task status and basic info - Called by backend API
def get_task_status_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves task status and basic information from the tasks table."""
    if PRIMARY_DB_TYPE != "postgresql":
         logger.warning(f"get_task_status_by_id only implemented for PostgreSQL, current type is {PRIMARY_DB_TYPE}")
         return None

    query = """
            SELECT task_id, user_id, file_id, requested_output_format, request_shakespearean_translation, requested_analysis_tasks, status, created_at, started_at, completed_at, error_message
            FROM tasks
            WHERE task_id = %s
            """
    params = (task_id,)
    row = _execute_query(query, params=params, fetchone=True)

    if row:
        # Convert JSONB strings back to Python objects automatically by DictCursor
        # task_info = dict(row) # DictCursor already returns a dict
        task_info = row # DictCursor result is already dict-like
        logger.debug(f"Task info retrieved: {task_id}, Status: {task_info['status']}", extra={'task_id': task_id})
        return task_info
    else:
        logger.warning(f"Task not found: {task_id}", extra={'task_id': task_id})
        return None


# Function to get detailed task results - Called by backend API
def get_task_result_details(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves detailed task results from the task_results table."""
    if PRIMARY_DB_TYPE != "postgresql":
         logger.warning(f"get_task_result_details only implemented for PostgreSQL, current type is {PRIMARY_DB_TYPE}")
         return None

    query = """
            SELECT task_id, final_status, processing_time_seconds, detailed_results, completed_at
            FROM task_results
            WHERE task_id = %s
            """
    params = (task_id,)
    row = _execute_query(query, params=params, fetchone=True)

    if row:
        # DictCursor automatically handles JSONB parsing
        # result_info = dict(row)
        result_info = row # DictCursor result is already dict-like
        logger.debug(f"Task result details retrieved: {task_id}", extra={'task_id': task_id, 'final_status': result_info['final_status']})
        return result_info
    else:
        logger.warning(f"Task result details not found for task: {task_id}", extra={'task_id': task_id})
        return None


# TODO: Implement create_user and get_user_by_email functions if user authentication is needed
# These would interact with the 'users' table

# Example (Conceptual):
# def create_user(email: str, hashed_password: str) -> bool:
#     if PRIMARY_DB_TYPE != "postgresql": return False
#     query = "INSERT INTO users (email, hashed_password) VALUES (%s, %s)"
#     params = (email, hashed_password)
#     result = _execute_query(query, params=params, commit=True)
#     if result is not None: logger.info(f"User created: {email}"); return True
#     return False

# def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
#     if PRIMARY_DB_TYPE != "postgresql": return None
#     query = "SELECT user_id, email, hashed_password FROM users WHERE email = %s"
#     params = (email,)
#     row = _execute_query(query, params=params, fetchone=True)
#     if row: return dict(row) # Return as dict
#     return None


# TODO: Implement get_file_location_by_file_id if needed (e.g., for a separate download service or worker retrieval)
# def get_file_location_by_file_id(file_id: str) -> Optional[Dict[str, Any]]:
#    if PRIMARY_DB_TYPE != "postgresql": return None
#    query = "SELECT storage_location FROM files WHERE file_id = %s"
#    params = (file_id,)
#    row = _execute_query(query, params=params, fetchone=True)
#    if row and row.get('storage_location'):
#        return dict(row['storage_location']) # Return the storage_location JSONB as dict
#    return None
