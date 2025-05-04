# e2e/config/config.py

import os

# --- General Configuration ---
# The URL of the deployed frontend application
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000") # Default to localhost

# Browser type to use for testing (chrome, firefox, etc.)
BROWSER = os.getenv("BROWSER", "chrome").lower()

# Implicit wait time (seconds)
IMPLICIT_WAIT = 10

# Default explicit wait timeout (seconds)
DEFAULT_WAIT_TIMEOUT = 30

# Path to the test file to upload (relative to where the script is run, or absolute)
# Consider using environment variables or pytest fixtures to manage test data paths more flexibly
TEST_FILE_PATH = os.getenv("TEST_FILE_PATH", "./test_sheet_music.pdf")


# --- Specific Wait Times (seconds) ---
# Define longer timeouts for steps involving asynchronous backend processing
WAIT_FOR_TASK_ITEM_APPEAR = 20
WAIT_FOR_STATUS_PROCESSING = 60
WAIT_FOR_STATUS_COMPLETED = 180 # Allow ample time for OMR, AI, music generation
WAIT_FOR_RESULT_DISPLAY = 10

# --- Browser Driver Paths (Optional if using webdriver_manager) ---
# DRIVER_PATH_CHROME = "/usr/local/bin/chromedriver" # Example path
# DRIVER_PATH_FIREFOX = "/usr/local/bin/geckodriver" # Example path
