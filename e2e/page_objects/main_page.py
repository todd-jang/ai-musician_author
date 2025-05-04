# e2e/page_objects/main_page.py

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
import os # To get filename

from .base_page import BasePage
from config.config import (
    FRONTEND_URL,
    WAIT_FOR_TASK_ITEM_APPEAR,
    WAIT_FOR_STATUS_PROCESSING,
    WAIT_FOR_STATUS_COMPLETED,
    WAIT_FOR_RESULT_DISPLAY
)

class MainPage(BasePage):
    """Page Object for the main application page (File Upload and Task List)."""

    # --- Locators (Find elements using these) ---
    # Define locators for elements on this page.
    # Use robust locators (ID, data-testid, unique CSS selectors, reliable XPATH)
    # Avoid brittle locators (absolute XPATH, complex nested CSS that might change)

    FILE_INPUT = (By.CSS_SELECTOR, 'input[type="file"]')
    UPLOAD_BUTTON = (By.XPATH, '//button[contains(., "Upload")]') # Assuming button text is "Upload"

    TASK_LIST_CONTAINER = (By.CSS_SELECTOR, '.task-list ul') # Assuming task list is an unordered list
    # Locator pattern for a specific task item based on filename or task ID
    def task_item_locator(self, filename: str):
        # Assuming each task item li contains the filename text
        # This locator finds an li element containing the filename, which is part of the task item
        return (By.XPATH, f'//li[contains(., "{os.path.basename(filename)}")]')

    # Locators for elements *within* a specific task item (relative to the task item element)
    STATUS_TEXT_RELATIVE = (By.XPATH, './/span[contains(., "Status:")]') # Finds a span with "Status:" text
    VIEW_RESULTS_BUTTON_RELATIVE = (By.XPATH, './/button[contains(., "View Results")]') # Finds "View Results" button

    TASK_DETAILS_MODAL_OVERLAY = (By.CSS_SELECTOR, '.task-details-overlay') # Locator for the modal overlay
    CLOSE_DETAILS_BUTTON = (By.XPATH, '//button[contains(., "Close")]') # Close button on the modal

    AUDIO_PLAYER = (By.CSS_SELECTOR, 'audio[controls]') # Assuming audio player is an audio tag


    # --- Methods (User actions on this page) ---

    def __init__(self, driver: WebDriver):
        super().__init__(driver)
        # Optional: Add check that you are on the correct page after opening
        # self.wait_until_visible((By.CSS_SELECTOR, 'h1'), timeout=10) # Wait for main heading

    def open_main_page(self):
        """Opens the main application page."""
        self.open(FRONTEND_URL)
        # Optional: Wait for the file input or upload button to be visible/clickable
        self.wait_until_clickable(self.FILE_INPUT)

    def select_file(self, file_path: str):
        """Selects a file using the file input."""
        # Selenium sends the file path directly to the hidden input
        file_input_element = self.find_element(self.FILE_INPUT)
        file_input_element.send_keys(file_path)
        print(f"Selected file: {os.path.basename(file_path)}")
        # Optional: Wait for the upload button to appear after file selection
        self.wait_until_clickable(self.UPLOAD_BUTTON)


    def click_upload_button(self):
        """Clicks the upload button."""
        upload_button_element = self.wait_until_clickable(self.UPLOAD_BUTTON)
        upload_button_element.click()
        print("Clicked Upload button.")
        # Optional: Wait for uploading indicator or task item to appear
        # self.wait_until_visible(self.task_item_locator("some_filename")) # Locator might need adjustment


    def get_task_item_element(self, filename: str):
        """Finds the DOM element for a specific task item."""
        locator = self.task_item_locator(filename)
        # Wait for the task item to appear in the list first
        return self.wait_until_visible(locator, timeout=WAIT_FOR_TASK_ITEM_APPEAR)

    def get_task_status_text(self, task_item_element):
        """Gets the status text from a task item element."""
        # Find the status span relative to the task item element
        status_span = task_item_element.find_element(*self.STATUS_TEXT_RELATIVE)
        return status_span.text # Get the visible text


    def wait_for_task_status(self, filename: str, status_text: str, timeout: int):
        """Waits for a specific task item to display a certain status text."""
        task_item_locator = self.task_item_locator(filename)
        # Wait for the task item to exist and then wait for the specific status text within it
        self.wait_until_text_in_element(task_item_locator, f'Status: {status_text}', timeout=timeout)
        print(f"Task '{os.path.basename(filename)}' status changed to: {status_text}")


    def wait_for_task_completed(self, filename: str):
        """Waits for a task to reach the 'Completed' status and for the view results button."""
        # Wait for the status text
        self.wait_for_task_status(filename, 'Completed', timeout=WAIT_FOR_STATUS_COMPLETED)
        # Wait for the View Results button to be clickable within the task item
        task_item_element = self.get_task_item_element(filename) # Get the updated element
        view_button = task_item_element.find_element(*self.VIEW_RESULTS_BUTTON_RELATIVE)
        self.wait_until_clickable((self.VIEW_RESULTS_BUTTON_RELATIVE[0], view_button.locator_to_string()), timeout=10) # Wait for the button within the item


    def click_view_results(self, filename: str):
        """Finds and clicks the 'View Results' button for a task."""
        task_item_element = self.get_task_item_element(filename)
        view_results_button = task_item_element.find_element(*self.VIEW_RESULTS_BUTTON_RELATIVE)
        view_results_button.click()
        print(f"Clicked 'View Results' for '{os.path.basename(filename)}'")
        # Optional: Wait for the modal to appear
        self.wait_until_visible(self.TASK_DETAILS_MODAL_OVERLAY)


    def wait_for_audio_player(self):
        """Waits for the audio player element to appear in the results modal."""
        audio_element = self.wait_until_visible(self.AUDIO_PLAYER, timeout=WAIT_FOR_RESULT_DISPLAY)
        # Optional: Wait for the src attribute to be present if it's set asynchronously
        # self.wait.until(lambda driver: audio_element.get_attribute('src'))
        print("Audio player appeared.")
        return audio_element # Return the element to check attributes

    def get_audio_player_src(self):
         """Gets the src attribute of the audio player."""
         audio_element = self.find_element(self.AUDIO_PLAYER)
         return audio_element.get_attribute('src')


    def close_task_details(self):
        """Clicks the close button on the task details modal."""
        close_button = self.wait_until_clickable(self.CLOSE_DETAILS_BUTTON)
        close_button.click()
        print("Clicked 'Close' button on modal.")
        # Wait for the modal to disappear
        self.wait_until_not_present(self.TASK_DETAILS_MODAL_OVERLAY)


    # Add methods for other interactions on the page (e.g., checking error messages, interacting with other tasks)
