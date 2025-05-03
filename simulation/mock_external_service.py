# simulation/mock_external_service.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import time
import random
import logging

# Configure simple logging for the mock service
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# --- Simulation Parameters (can be controlled via environment variables) ---
SIMULATE_DELAY_SECONDS = float(os.getenv("SIMULATE_DELAY_SECONDS", 0.0))
SIMULATE_ERROR_RATE = float(os.getenv("SIMULATE_ERROR_RATE", 0.0)) # 0.0 to 1.0
SIMULATE_ERROR_STATUS_CODE = int(os.getenv("SIMULATE_ERROR_STATUS_CODE", 500))
# Specific error codes could be simulated (e.g., 429 for rate limit)
SIMULATE_RATE_LIMIT_ENABLED = os.getenv("SIMULATE_RATE_LIMIT_ENABLED", "false").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))

# Basic rate limiting state (for simulation)
request_timestamps = []

# --- Helper function for rate limiting ---
def check_rate_limit():
    if not SIMULATE_RATE_LIMIT_ENABLED:
        return True

    now = time.time()
    # Keep only timestamps from the last minute
    one_minute_ago = now - 60
    global request_timestamps
    request_timestamps = [ts for ts in request_timestamps if ts > one_minute_ago]

    if len(request_timestamps) >= RATE_LIMIT_PER_MINUTE:
        logger.warning("Simulated rate limit exceeded.")
        return False
    
    request_timestamps.append(now)
    return True


# --- Mock Endpoint mimicking OpenAI Translation API ---
# This endpoint structure depends on how the worker calls the OpenAI API.
# Assuming a simple POST request with text in the body.
# If using Chat Completions API, the structure will be different.
# Example: Mimicking a hypothetical '/v1/engines/davinci/completions' or similar endpoint
@app.post("/v1/chat/completions") # Example based on OpenAI Chat Completions API endpoint
async def mock_openai_completion(request: Request):
    logger.info(f"Mock OpenAI received request.")

    # Simulate delay
    if SIMULATE_DELAY_SECONDS > 0:
        logger.info(f"Simulating delay of {SIMULATE_DELAY_SECONDS} seconds.")
        time.sleep(SIMULATE_DELAY_SECONDS)

    # Simulate rate limit
    if not check_rate_limit():
         logger.error(f"Simulated rate limit exceeded, returning {429}.")
         raise HTTPException(status_code=429, detail="Simulated Rate Limit Exceeded")


    # Simulate random error
    if random.random() < SIMULATE_ERROR_RATE:
        logger.error(f"Simulating random error, returning {SIMULATE_ERROR_STATUS_CODE}.")
        raise HTTPException(status_code=SIMULATE_ERROR_STATUS_CODE, detail="Simulated Random Error")

    # Process the request body (assuming it contains the text to translate)
    try:
        request_body = await request.json()
        # In a real mock, you might parse the messages array to find the user prompt
        # For simplicity, we'll just return a fixed mock response
        # input_text = request_body.get("prompt", "default text") # If using Completions API
        # If using Chat Completions API, parse messages
        input_messages = request_body.get("messages", [])
        input_text = input_messages[-1].get("content", "default text") if input_messages else "default text"
        logger.info(f"Received text for mock translation: {input_text[:50]}...")

    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        raise HTTPException(status_code=400, detail="Invalid request body format")


    # --- Simulate successful response ---
    # Return a mock response mimicking the OpenAI API format
    mock_translated_text = f"Hark! This is mock'd Shakespearian for '{input_text}'."
    
    # Mock response structure for Chat Completions API
    mock_response = {
      "id": f"chatcmpl-{uuid.uuid4()}",
      "object": "chat.completion",
      "created": int(time.time()),
      "model": "gpt-3.5-turbo", # Or the model being mocked
      "choices": [
        {
          "index": 0,
          "message": {
            "role": "assistant",
            "content": mock_translated_text,
          },
          "logprobs": None,
          "finish_reason": "stop"
        }
      ],
      "usage": {
        "prompt_tokens": 10, # Mock token counts
        "completion_tokens": 20,
        "total_tokens": 30
      }
    }


    logger.info("Returning simulated successful response.")
    return JSONResponse(content=mock_response, status_code=200)


# --- Main entry point for running the mock server ---
if __name__ == "__main__":
    # Define the host and port for the mock server
    MOCK_HOST = os.getenv("MOCK_HOST", "0.0.0.0")
    MOCK_PORT = int(os.getenv("MOCK_PORT", 8080))

    logger.info(f"Mock external service starting on {MOCK_HOST}:{MOCK_PORT}")
    logger.info(f"Simulation parameters: Delay={SIMULATE_DELAY_SECONDS}s, ErrorRate={SIMULATE_ERROR_RATE}, ErrorCode={SIMULATE_ERROR_STATUS_CODE}")
    if SIMULATE_RATE_LIMIT_ENABLED:
         logger.info(f"  Rate Limit Enabled: {RATE_LIMIT_PER_MINUTE}/minute")

    uvicorn.run(app, host=MOCK_HOST, port=MOCK_PORT)
