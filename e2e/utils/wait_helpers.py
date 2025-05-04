# e2e/utils/wait_helpers.py

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config.config import DEFAULT_WAIT_TIMEOUT

def wait_for_element_visible(driver: WebDriver, locator: tuple, timeout: int = DEFAULT_WAIT_TIMEOUT):
    """Waits for an element to be visible on the page."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )
        return element
    except TimeoutException:
        print(f"Timeout waiting for element located by {locator} to be visible.")
        raise # Re-raise the exception

def wait_for_element_clickable(driver: WebDriver, locator: tuple, timeout: int = DEFAULT_WAIT_TIMEOUT):
    """Waits for an element to be clickable on the page."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        return element
    except TimeoutException:
        print(f"Timeout waiting for element located by {locator} to be clickable.")
        raise

def wait_for_text_in_element(driver: WebDriver, locator: tuple, text: str, timeout: int = DEFAULT_WAIT_TIMEOUT):
    """Waits for specific text to be present in an element."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.text_to_be_present_in_element(locator, text)
        )
    except TimeoutException:
        print(f"Timeout waiting for text '{text}' in element located by {locator}.")
        raise

def wait_for_element_not_present(driver: WebDriver, locator: tuple, timeout: int = DEFAULT_WAIT_TIMEOUT):
     """Waits for an element to no longer be present in the DOM."""
     try:
         WebDriverWait(driver, timeout).until(
             EC.invisibility_of_element_located(locator) # Checks for both not present or not visible
         )
     except TimeoutException:
         print(f"Timeout waiting for element located by {locator} to disappear or become invisible.")
         raise

# Add other common wait helpers as needed
