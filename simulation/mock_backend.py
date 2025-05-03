# simulation/mock_backend.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import logging
import os
import time

# Configure simple logging for the mock backend
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Define the endpoint that the API Gateway will route to
# This path should match the internal path expected by the Gateway configuration
@app.post("/upload_sheetmusic")
async def mock_upload_sheet_music(request: Request):
    """
    Mock endpoint for /upload_sheetmusic.
    Simulates the backend receiving an upload request from the API Gateway.
    """
    logger.info(f"Mock Backend received POST request at /upload_sheetmusic")

    # Optional: Read and log parts of the request to confirm it was received correctly
    try:
        # Access form data for file uploads
        form_data = await request.form()
        uploaded_file = form_data.get('file')
        original_filename = uploaded_file.filename if uploaded_file else 'N/A'
        logger.info(f"Received file upload request for: {original_filename}")
        # You could potentially read the file content here if needed for a more complex mock
        # content = await uploaded_file.read()

        # Access query parameters
        query_params = dict(request.query_params)
        logger.info(f"Received query parameters: {query_params}")

    except Exception as e:
        logger.error(f"Failed to parse request in mock backend: {e}", exc_info=True)
        # Return a 400 error for bad requests
        raise HTTPException(status_code=400, detail=f"Mock backend failed to parse request: {e}")


    # --- Simulate a simple successful response ---
    # This response mimics the *format* of the real backend's success response
    # but doesn't involve actual task queuing or processing.
    # We can return a dummy task_id or generate one if needed for logging
    mock_task_id = f"mock-task-{int(time.time())}-{random.randint(1000, 9999)}"

    mock_response_content = {
        "message": "Request received by mock backend and simulated queuing.",
        "task_id": mock_task_id, # Return a mock task ID
        "uploaded_s3_key": f"mock/uploads/{original_filename}", # Mock storage key
        "status": "processing_queued" # Indicate success in receiving request
    }

    logger.info("Mock Backend returning simulated success response.")
    return JSONResponse(content=mock_response_content, status_code=200)


# Add other endpoints if the API Gateway routes to them for testing
# @app.get("/status/{task_id}")
# async def mock_get_task_status(task_id: str):
#     logger.info(f"Mock Backend received GET request for status: {task_id}")
#     # Simulate a mock status response
#     mock_status_response = {
#         "task_id": task_id,
#         "status": "mock_status_completed",
#         "detail": f"This is a mock status for {task_id}"
#     }
#     return JSONResponse(content=mock_status_response, status_code=200)


# --- Main entry point for running the mock backend server ---
if __name__ == "__main__":
    # Define the host and port for the mock backend server
    MOCK_BACKEND_HOST = os.getenv("MOCK_BACKEND_HOST", "0.0.0.0")
    MOCK_BACKEND_PORT = int(os.getenv("MOCK_BACKEND_PORT", 8001)) # Use a different port than real backend (8000)

    logger.info(f"Mock Backend service starting on {MOCK_BACKEND_HOST}:{MOCK_BACKEND_PORT}")

    # Run the FastAPI application
    uvicorn.run(app, host=MOCK_BACKEND_HOST, port=MOCK_BACKEND_PORT)
