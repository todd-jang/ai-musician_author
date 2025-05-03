// frontend/src/services/apiService.js (Conceptual API Service)

import httpx from 'httpx'; // Using httpx for example (install: npm install httpx or yarn add httpx)
// If not using httpx, use Fetch API or Axios (npm install axios or yarn add axios)
// import axios from 'axios';

// Define your backend API base URL (e.g., from environment variables or a config file)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'; // Default local backend URL
// If using API Gateway, this URL would be the API Gateway's public URL
// const API_BASE_URL = process.env.REACT_APP_API_GATEWAY_URL || 'http://localhost'; // Example API Gateway URL

// Use httpx Client for potential connection pooling (good practice)
// const client = httpx.Client({ baseURL: API_BASE_URL, timeout: 30.0 }); // Set a default timeout

const apiService = {
    // --- File Upload API Call ---
    uploadFile: async (file, options = {}, onProgress) => {
        const formData = new FormData();
        formData.append('file', file); // 'file' is the field name expected by FastAPI backend

        // Add other options as form fields or query parameters as expected by your backend
        // Assuming backend expects them as query parameters for the upload endpoint
        // If they are part of the JSON payload, use client.post(url, json={...})
        const queryParams = new URLSearchParams();
        if (options.output_format) {
            queryParams.append('output_format', options.output_format);
        }
        if (options.translate_shakespearean !== undefined) {
            queryParams.append('translate_shakespearean', options.translate_shakespearean);
        }
        // Add other options

        const url = `${API_BASE_URL}/music/upload_sheetmusic?${queryParams.toString()}`;

        try {
            // Using Fetch API for upload with progress
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                // headers: { 'Content-Type': 'multipart/form-data' }, // Fetch API sets this automatically for FormData
            });

            // Basic progress tracking with Fetch API is more complex, often requires ReadableStream
            // Axios provides easier progress tracking with onUploadProgress option.
            // Example with Axios:
            /*
            const axiosResponse = await axios.post(url, formData, {
                onUploadProgress: (progressEvent) => {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    onProgress(percentCompleted); // Call the progress callback
                },
                // headers: { 'Content-Type': 'multipart/form-data' }, // Axios also sets this
            });
            return axiosResponse.data; // Axios puts response body in .data
            */

             // Fallback progress for Fetch (estimates 50% when request starts, 100% on response)
            if (onProgress) {
                onProgress(10); // Started sending
                 // Note: Accurate progress requires more advanced Fetch API usage or Axios
            }


            if (!response.ok) {
                // Handle HTTP errors (e.g., 400, 500)
                const errorDetail = await response.text(); // Get error message from body
                throw new Error(`HTTP error ${response.status}: ${errorDetail}`);
            }

            if (onProgress) {
                 onProgress(100); // Finished sending and got response header
            }

            // Parse JSON response from backend
            const responseData = await response.json();
            return responseData;

        } catch (error) {
            console.error("API uploadFile failed:", error);
            throw error; // Re-throw for component to handle
        }
    },

    // --- Get Task Status API Call ---
    getTaskStatus: async (taskId) => {
        const url = `${API_BASE_URL}/status/${taskId}`; // Assuming a /status/{task_id} endpoint

        try {
            const response = await fetch(url); // Using Fetch API

            if (!response.ok) {
                if (response.status === 404) {
                    // Task not found
                    return { status: 'not_found' }; // Indicate task not found
                }
                const errorDetail = await response.text();
                throw new Error(`HTTP error ${response.status}: ${errorDetail}`);
            }

            const statusData = await response.json();
            return statusData; // Expected format: { task_id, status, ... }

        } catch (error) {
            console.error(`API getTaskStatus failed for ${taskId}:`, error);
            throw error;
        }
    },

     // --- Get Task Result API Call ---
    getTaskResult: async (taskId) => {
        const url = `${API_BASE_URL}/results/${taskId}`; // Assuming a /results/{task_id} endpoint

        try {
            const response = await fetch(url); // Using Fetch API

            if (!response.ok) {
                const errorDetail = await response.text();
                throw new Error(`HTTP error ${response.status}: ${errorDetail}`);
            }

            const resultData = await response.json();
            return resultData; // Expected format: { task_id, final_status, detailed_results, ... }

        } catch (error) {
            console.error(`API getTaskResult failed for ${taskId}:`, error);
            throw error;
        }
    },

    // TODO: Add other API calls if needed (e.g., login, signup, get user tasks)
};

export default apiService;
