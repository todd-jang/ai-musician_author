# e2e/fixtures/conftest.py

import pytest
from selenium import webdriver
# From webdriver_manager for easier driver handling
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager

from config.config import BROWSER, IMPLICIT_WAIT


@pytest.fixture(scope="session") # Fixture scope: "session" means driver is created once per test session
def driver():
    """Provides a WebDriver instance for tests."""
    print(f"\nSetting up WebDriver for browser: {BROWSER}")

    if BROWSER == "chrome":
        # Automatically download and manage ChromeDriver
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
    elif BROWSER == "firefox":
        # Automatically download and manage GeckoDriver
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service)
    # Add other browser options (edge, safari, headless) here
    else:
        raise ValueError(f"Unsupported browser: {BROWSER}")

    # Set implicit wait
    driver.implicitly_wait(IMPLICIT_WAIT)

    # Optional: Maximize window
    driver.maximize_window()

    yield driver # Provide the driver instance to the test

    # Teardown: This code runs after the test session is finished
    print("\nQuitting WebDriver.")
    driver.quit()
