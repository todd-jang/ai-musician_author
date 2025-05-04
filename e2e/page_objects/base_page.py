# e2e/page_objects/base_page.py

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.config import DEFAULT_WAIT_TIMEOUT
from utils.wait_helpers import (
    wait_for_element_visible,
    wait_for_element_clickable,
    wait_for_text_in_element,
    wait_for_element_not_present
)

class BasePage:
    """Base class for all Page Objects."""

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait = WebDriverWait(driver, DEFAULT_WAIT_TIMEOUT) # Common wait object

    def open(self, url: str):
        """Navigates to a given URL."""
        self.driver.get(url)
        print(f"Navigated to {url}")

    def find_element(self, locator: tuple):
        """Finds an element using a locator."""
        return self.driver.find_element(*locator)

    def find_elements(self, locator: tuple):
         """Finds multiple elements using a locator."""
         return self.driver.find_elements(*locator)

    # Add common wait methods from utils
    def wait_until_visible(self, locator: tuple, timeout: int = DEFAULT_WAIT_TIMEOUT):
        return wait_for_element_visible(self.driver, locator, timeout)

    def wait_until_clickable(self, locator: tuple, timeout: int = DEFAULT_WAIT_TIMEOUT):
        return wait_for_element_clickable(self.driver, locator, timeout)

    def wait_until_text_in_element(self, locator: tuple, text: str, timeout: int = DEFAULT_WAIT_TIMEOUT):
        wait_for_text_in_element(self.driver, locator, text, timeout)

    def wait_until_not_present(self, locator: tuple, timeout: int = DEFAULT_WAIT_TIMEOUT):
         wait_for_element_not_present(self.driver, locator, timeout)

    # Add other common page methods (e.g., get page title, take screenshot)
