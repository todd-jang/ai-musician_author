# simulate_load.py

import httpx # Or 'requests'
import os
import sys
import time
import threading
import argparse
import io # For file object
import logging

# Configure simple logging for the simulation script itself
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Configuration ---
# Backend API URL (when running with Docker Compose)
# If using Traefik, use Traefik endpoint. If exposing backend directly, use backend service port.
# Example using backend service directly exposed on 8000:
# BACKEND_API_URL = "http://localhost:8000"
# Example using Traefik routing:
BACKEND_API_URL = "http://localhost" # Assuming Traefik is on default HTTP port 80

# Endpoint path for uploading sheet music
UPLOAD_ENDPOINT_PATH = "/music/upload_sheetmusic"

# Path to a test file to upload (a small, representative file is good)
TEST_FILE_PATH = "./test_sheet_music.pdf" # Replace with path to a small PDF or image file

# Simulation parameters
NUM_REQUESTS = 100 # Total number of task requests to send
CONCURRENCY = 10   # Number of requests to send concurrently
OUTPUT_FORMAT = "mp3" # Requested output format for the task
TRANSLATE_SHAKESPEAREAN = False # Request Shakespearean translation


# --- Helper function to send a single upload request ---
def send_upload_request(client: httpx.Client, request_num: int):
    url = f"{BACKEND_API_URL}{UPLOAD_ENDPOINT_PATH}"
    file_name = os.path.basename(TEST_FILE_PATH)
    unique_file_name = f"{request_num}_{int(time.time())}_{file_name}" # Make filename somewhat unique
    
    # Prepare the file object for uploading
    try:
        with open(TEST_FILE_PATH, "rb") as f:
            # httpx expects files parameter as a dictionary of {name: file_tuple}
            # file_tuple is (filename, file_like_object, content_type)
            files = {'file': (unique_file_name, io.BytesIO(f.read()), 'application/pdf')} # Read file content into BytesIO
    except FileNotFoundError:
        logger.error(f"Test file not found: {TEST_FILE_PATH}")
        return None, None # Return None on failure
        
    # Prepare query parameters
    params = {
        "output_format": OUTPUT_FORMAT,
        "translate_shakespearean": str(TRANSLATE_SHAKESPEAREAN).lower() # Convert boolean to string
    }

    start_time = time.time()
    task_id = None
    try:
        # Send the POST request
        response = client.post(url, files=files, params=params, timeout=30.0) # Add a timeout

        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        end_time = time.time()
        duration = end_time - start_time

        # Process successful response
        response_data = response.json()
        task_id = response_data.get("task_id", "N/A")
        status = response_data.get("status", "N/A")

        logger.info(f"Request {request_num}: Success - Status: {status}, Task ID: {task_id}, Duration: {duration:.2f}s")
        return task_id, duration

    except httpx.RequestError as e:
        end_time = time.time()
        duration = end_time - start_time
        logger.error(f"Request {request_num}: Failed - Network/Request Error: {e}, Duration: {duration:.2f}s")
        return None, duration
    except httpx.HTTPStatusError as e:
        end_time = time.time()
        duration = end_time - start_time
        logger.error(f"Request {request_num}: Failed - HTTP Error: {e.response.status_code} {e.response.reason}, Duration: {duration:.2f}s, Response Body: {e.response.text[:100]}...")
        return None, duration
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        logger.error(f"Request {request_num}: Failed - Unexpected Error: {e}, Duration: {duration:.2f}s", exc_info=True)
        return None, duration


# --- Main simulation logic ---
def run_simulation(num_requests: int, concurrency: int):
    logger.info(f"Starting simulation: Sending {num_requests} requests with concurrency {concurrency}")

    # Use httpx.Client for connection pooling in concurrent requests
    # Use a ThreadPoolExecutor for managing concurrent requests
    from concurrent.futures import ThreadPoolExecutor

    results = [] # Store results (task_id, duration)
    start_time = time.time()

    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            # Submit requests to the executor
            future_to_request = {executor.submit(send_upload_request, client, i + 1): i + 1 for i in range(num_requests)}

            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_request):
                request_num = future_to_request[future]
                try:
                    task_id, duration = future.result()
                    results.append({"request_num": request_num, "task_id": task_id, "duration": duration, "success": task_id is not None})
                except Exception as exc:
                    logger.error(f"Request {request_num} generated an exception: {exc}")
                    results.append({"request_num": request_num, "task_id": None, "duration": None, "success": False})

    end_time = time.time()
    total_duration = end_time - start_time

    logger.info("Simulation finished.")
    logger.info(f"Total requests sent: {num_requests}")
    logger.info(f"Total simulation duration: {total_duration:.2f}s")

    successful_requests = sum(1 for r in results if r["success"])
    failed_requests = num_requests - successful_requests
    logger.info(f"Successful requests: {successful_requests}")
    logger.info(f"Failed requests: {failed_requests}")

    # Optional: Analyze durations or other results
    # durations = [r["duration"] for r in results if r["success"]]
    # if durations:
    #     logger.info(f"Average successful request duration: {sum(durations) / len(durations):.2f}s")
    #     logger.info(f"Max successful request duration: {max(durations):.2f}s")
    #     logger.info(f"Min successful request duration: {min(durations):.2f}s")


# --- Command line execution ---
if __name__ == "__main__":
    # Ensure a test file exists
    if not os.path.exists(TEST_FILE_PATH):
        logger.error(f"Error: Test file not found at {TEST_FILE_PATH}. Please create one.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Simulate load on the Personal Data Assistant backend.")
    parser.add_argument("--requests", type=int, default=NUM_REQUESTS, help="Total number of requests to send.")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY, help="Number of concurrent requests.")
    parser.add_argument("--file", type=str, default=TEST_FILE_PATH, help="Path to the test file to upload.")
    parser.add_argument("--output", type=str, default=OUTPUT_FORMAT, choices=['midi', 'mp3'], help="Requested output format.")
    parser.add_argument("--translate", action="store_true", default=TRANSLATE_SHAKESPEAREAN, help="Request Shakespearean translation.")
    parser.add_argument("--api-url", type=str, default=BACKEND_API_URL, help="Base URL of the backend API.")


    args = parser.parse_args()

    # Update configuration from arguments
    NUM_REQUESTS = args.requests
    CONCURRENCY = args.concurrency
    TEST_FILE_PATH = args.file
    OUTPUT_FORMAT = args.output
    TRANSLATE_SHAKESPEAREAN = args.translate
    BACKEND_API_URL = args.api_url

    logger.info("Simulation configuration:")
    logger.info(f"  API URL: {BACKEND_API_URL}")
    logger.info(f"  Upload Endpoint: {UPLOAD_ENDPOINT_PATH}")
    logger.info(f"  Test File: {TEST_FILE_PATH}")
    logger.info(f"  Number of Requests: {NUM_REQUESTS}")
    logger.info(f"  Concurrency: {CONCURRENCY}")
    logger.info(f"  Requested Output: {OUTPUT_FORMAT}")
    logger.info(f"  Translate Shakespearean: {TRANSLATE_SHAKESPEAREAN}")


    # Ensure updated test file path exists
    if not os.path.exists(TEST_FILE_PATH):
        logger.error(f"Error: Test file not found at {TEST_FILE_PATH}.")
        sys.exit(1)


    run_simulation(NUM_REQUESTS, CONCURRENCY)
