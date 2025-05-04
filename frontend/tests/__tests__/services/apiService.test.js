// frontend/tests/__tests__/services/apiService.test.js

import '@testing-library/jest-dom'; // For fetchMock type definitions
import apiService from '../../../src/services/apiService';
import 'jest-fetch-mock'; // Already enabled and reset in setupTests.js

describe('apiService', () => {

    // fetchMock is available globally after importing 'jest-fetch-mock' and calling enableMocks/resetMocks in setupTests.js

    const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'; // Match service file logic

    beforeEach(() => {
        // fetchMock.resetMocks(); // Handled by setupTests.js
    });

    test('uploadFile sends correct POST request with file and options', async () => {
        // Arrange: Mock a successful backend response
        const mockResponseData = {
            message: "Upload successful",
            task_id: "abc-123",
            uploaded_s3_key: "uploads/my_score.pdf",
            status: "processing_queued"
        };
        // Configure fetchMock to return a successful JSON response
        fetchMock.mockResponseOnce(JSON.stringify(mockResponseData), { status: 200 });

        // Arrange: Define mock file and options
        const mockFile = new File(['dummy content'], 'my_score.pdf', { type: 'application/pdf' });
        const mockOptions = {
            output_format: 'mp3',
            translate_shakespearean: true
        };
        const mockOnProgress = jest.fn(); // Mock progress callback

        // Act: Call the uploadFile function
        const result = await apiService.uploadFile(mockFile, mockOptions, mockOnProgress);

        // Assert: Check if fetch was called with the correct URL and options
        expect(fetch).toHaveBeenCalledTimes(1);
        const expectedUrl = `${API_BASE_URL}/music/upload_sheetmusic?output_format=mp3&translate_shakespearean=true`;
        // Check the URL including query parameters
        expect(fetch).toHaveBeenCalledWith(
             expect.stringContaining(API_BASE_URL + '/music/upload_sheetmusic'), // Basic path check
             expect.anything() // We'll check method and body separately
        );
        // Check if the query parameters are included
        const fetchCallArgs = fetch.mock.calls[0][0]; // Get the URL argument from the fetch call
         expect(fetchCallArgs).toContain('output_format=mp3');
         expect(fetchCallArgs).toContain('translate_shakespearean=true');


        // Check the request method and body (FormData)
        const fetchOptions = fetch.mock.calls[0][1]; // Get the options argument from the fetch call
        expect(fetchOptions.method).toBe('POST');
        expect(fetchOptions.body).toBeInstanceOf(FormData); // Ensure body is FormData

        // You can optionally inspect the FormData contents (more complex)
        // For FormData, checking if the correct file is appended is a good test
        const formData = fetchOptions.body;
        expect(formData.get('file')).toBeInstanceOf(File);
        expect(formData.get('file').name).toBe('my_score.pdf');
        // Check other form fields if options were appended as form fields instead of query params

        // Assert: Check the returned data matches the mock response
        expect(result).toEqual(mockResponseData);

        // Assert: Check if the progress callback was called (basic Fetch progress is limited)
        // Based on our simple Fetch progress in apiService, it should be called at least twice (10% and 100%)
        expect(mockOnProgress).toHaveBeenCalled();
        // expect(mockOnProgress).toHaveBeenCalledWith(10); // Example based on the simple implementation
        // expect(mockOnProgress).toHaveBeenCalledWith(100);
        // For accurate progress testing, use Axios and mock onUploadProgress callbacks.

    });

    test('uploadFile handles HTTP error response', async () => {
        // Arrange: Mock an error response (e.g., 400 Bad Request)
        const mockErrorBody = "Unsupported file format";
        fetchMock.mockResponseOnce(mockErrorBody, { status: 400, statusText: 'Bad Request' });

        const mockFile = new File(['dummy content'], 'invalid.txt', { type: 'text/plain' });
        const mockOptions = { output_format: 'midi' };
        const mockOnProgress = jest.fn();

        // Act & Assert: Expect the function to throw an error
        await expect(apiService.uploadFile(mockFile, mockOptions, mockOnProgress)).rejects.toThrow(
            'HTTP error 400: Unsupported file format' // Match the error message thrown by apiService
        );

        // Assert: Fetch was called
        expect(fetch).toHaveBeenCalledTimes(1);
        // Progress callback might be called before the error
        expect(mockOnProgress).toHaveBeenCalled();

    });

    test('getTaskStatus sends correct GET request and returns data on success', async () => {
        // Arrange: Mock a successful status response
        const taskId = 'task-abc';
        const mockStatusData = { task_id: taskId, status: 'processing' };
        fetchMock.mockResponseOnce(JSON.stringify(mockStatusData), { status: 200 });

        // Act: Call the getTaskStatus function
        const statusResult = await apiService.getTaskStatus(taskId);

        // Assert: Check if fetch was called with the correct URL
        expect(fetch).toHaveBeenCalledTimes(1);
        expect(fetch).toHaveBeenCalledWith(`${API_BASE_URL}/status/${taskId}`, expect.anything()); // Check URL and default options

        // Assert: Check the returned data
        expect(statusResult).toEqual(mockStatusData);
    });

     test('getTaskStatus returns "not_found" status for 404 response', async () => {
        // Arrange: Mock a 404 Not Found response
        const taskId = 'non-existent-task';
        fetchMock.mockResponseOnce("Not Found", { status: 404, statusText: 'Not Found' });

        // Act: Call the getTaskStatus function
        const statusResult = await apiService.getTaskStatus(taskId);

        // Assert: Check if fetch was called
        expect(fetch).toHaveBeenCalledTimes(1);
        expect(fetch).toHaveBeenCalledWith(`${API_BASE_URL}/status/${taskId}`, expect.anything());

        // Assert: Check the returned status indicator
        expect(statusResult).toEqual({ status: 'not_found' });
    });


    test('getTaskStatus throws error for other HTTP errors (non-404)', async () => {
        // Arrange: Mock a 500 Internal Server Error response
        const taskId = 'task-error';
        fetchMock.mockResponseOnce("Internal Server Error", { status: 500, statusText: 'Internal Server Error' });

        // Act & Assert: Expect the function to throw an error
        await expect(apiService.getTaskStatus(taskId)).rejects.toThrow(
            'HTTP error 500: Internal Server Error'
        );

        // Assert: Check if fetch was called
        expect(fetch).toHaveBeenCalledTimes(1);
        expect(fetch).toHaveBeenCalledWith(`${API_BASE_URL}/status/${taskId}`, expect.anything());
    });


     test('getTaskResult sends correct GET request and returns data on success', async () => {
        // Arrange: Mock a successful result response
        const taskId = 'task-def';
        const mockResultData = {
            task_id: taskId,
            final_status: 'completed',
            detailed_results: { music_url: 'http://example.com/music.mp3' }
        };
        fetchMock.mockResponseOnce(JSON.stringify(mockResultData), { status: 200 });

        // Act: Call the getTaskResult function
        const result = await apiService.getTaskResult(taskId);

        // Assert: Check if fetch was called with the correct URL
        expect(fetch).toHaveBeenCalledTimes(1);
        expect(fetch).toHaveBeenCalledWith(`${API_BASE_URL}/results/${taskId}`, expect.anything());

        // Assert: Check the returned data
        expect(result).toEqual(mockResultData);
    });

     test('getTaskResult throws error for HTTP error response', async () => {
        // Arrange: Mock an error response (e.g., 404 or 500)
        const taskId = 'task-no-result';
        fetchMock.mockResponseOnce("Result not found", { status: 404, statusText: 'Not Found' });

        // Act & Assert: Expect the function to throw an error
        await expect(apiService.getTaskResult(taskId)).rejects.toThrow(
            'HTTP error 404: Result not found'
        );

        // Assert: Check if fetch was called
        expect(fetch).toHaveBeenCalledTimes(1);
        expect(fetch).toHaveBeenCalledWith(`${API_BASE_URL}/results/${taskId}`, expect.anything());
    });


    // TODO: Add tests for other apiService functions (e.g., login, signup, get user tasks)

});
