// frontend/tests/setupTests.js
// This file is automatically run by Jest before tests.

import '@testing-library/jest-dom'; // Extends Jest matchers for DOM assertions
import 'jest-fetch-mock'; // Setup fetch mocking


// Enable fetch mocks globally
fetchMock.enableMocks();

// Reset mocks before each test
beforeEach(() => {
  fetchMock.resetMocks();
});
