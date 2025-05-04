# e2e/tests/test_mvp_flow.py

import pytest
from selenium.webdriver.remote.webdriver import WebDriver # Type hinting
import os # For test file path

# Import Page Objects
from page_objects.main_page import MainPage

# Import Config
from config.config import TEST_FILE_PATH

# No need to import webdriver here, it's provided by the 'driver' fixture from conftest.py


def test_mvp_upload_to_completed_flow(driver: WebDriver):
    """
    Tests the core MVP user flow: file upload, waiting for completion,
    viewing results, and closing the details.
    """
    print("\nExecuting test_mvp_upload_to_completed_flow")

    # --- Arrange ---
    # Create a Page Object instance for the main page
    main_page = MainPage(driver)

    # --- Act 1: Open the main page ---
    main_page.open_main_page()

    # --- Act 2: Select a file and click upload ---
    # Ensure the test file exists where the script is run
    if not os.path.exists(TEST_FILE_PATH):
         pytest.skip(f"Test file not found at {TEST_FILE_PATH}. Skipping test.")

    main_page.select_file(TEST_FILE_PATH)
    main_page.click_upload_button()

    # --- Assert & Act 3: Wait for task status changes and completion ---
    # Use Page Object methods to wait for UI states
    # The Page Object methods encapsulate the explicit waits
    filename = os.path.basename(TEST_FILE_PATH)

    # Wait for the task item to appear with initial status (e.g., 'uploading' or 'queued')
    # This might happen quickly after clicking upload, but worth a small wait if needed.
    # main_page.wait_for_task_status(filename, 'uploading', timeout=10) # If UI shows 'uploading' first

    # Wait for status to transition to 'processing_queued' or 'queued' after upload API response
    main_page.wait_for_task_status(filename, 'processing_queued', timeout=20) # Or 'queued'

    # Wait for status to transition to 'Processing...' (after worker picks up)
    main_page.wait_for_task_status(filename, 'Processing...', timeout=config.WAIT_FOR_STATUS_PROCESSING) # Use config timeout

    # Wait for status to transition to 'Completed' (after worker finishes)
    # This also waits for the "View Results" button to be clickable
    main_page.wait_for_task_completed(filename) # Encapsulates waiting for status and button

    print(f"Task for {filename} reached 'Completed' status.")


    # --- Act 4: Click "View Results" and verify modal/results display ---
    main_page.click_view_results(filename)

    # Wait for the audio player (or other result indicator) to appear in the modal
    audio_element = main_page.wait_for_audio_player()

    # Assert: Check the src attribute of the audio player (must point to a valid URL)
    audio_src = audio_element.get_attribute('src')
    print(f"Audio source found: {audio_src}")
    assert audio_src and audio_src.startswith('http'), f"Expected audio src to be an http URL, but got {audio_src}"

    # Optional: Verify other result elements (translated text etc.) using Page Object methods


    # --- Act 5: Close the details modal ---
    main_page.close_task_details()

    print("Test finished.")
