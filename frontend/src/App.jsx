// frontend/src/index.jsx or frontend/src/App.jsx (Root Component)

import React, { useState, useEffect } from 'react';
import FileUploader from './components/FileUploader';
import TaskList from './components/TaskList';
import TaskDetails from './components/TaskDetails';
import Header from './components/Header';
import apiService from './services/apiService'; // We will define this

function App() {
    // --- State Management ---
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploadProgress, setUploadProgress] = useState(0); // 0-100
    const [tasks, setTasks] = useState([]); // List of {id, filename, status, ...}
    const [selectedTask, setSelectedTask] = useState(null); // Task ID or object for details view
    const [isLoading, setIsLoading] = useState(false); // Global loading state

    // --- File Input Handling ---
    // Handled within FileUploader component, but the file object is passed up.
    const handleFileSelect = (file) => {
        setSelectedFile(file);
        setUploadProgress(0); // Reset progress on new selection
        // Optional: Add file to a list of pending uploads here
    };

    // --- File Upload Logic ---
    const handleUpload = async () => {
        if (!selectedFile) {
            alert("Please select a file first.");
            return;
        }

        setIsLoading(true); // Start loading spinner or similar
        setUploadProgress(0); // Ensure progress starts at 0

        const taskId = `task-${Date.now()}-${Math.random().toString(36).substring(7)}`; // Generate a temporary client-side ID or use backend ID

        // Add a placeholder task to the list immediately
        const newTask = {
            id: taskId, // Use a client-side ID initially
            filename: selectedFile.name,
            status: 'uploading',
            uploadProgress: 0,
            backendTaskId: null, // Will be filled by backend response
            result: null,
            error: null
        };
        setTasks(prevTasks => [...prevTasks, newTask]);

        try {
            // Call the API service to handle the actual HTTP request
            // apiService.uploadFile is a function we need to implement
            const responseData = await apiService.uploadFile(
                selectedFile,
                { output_format: 'mp3', translate_shakespearean: true }, // Example options
                (progress) => {
                    // Update upload progress state as file is being sent
                    setUploadProgress(progress);
                    // Also update the specific task item's progress
                    setTasks(prevTasks => prevTasks.map(task =>
                        task.id === taskId ? { ...task, uploadProgress: progress } : task
                    ));
                }
            );

            // Handle backend response
            if (responseData && responseData.task_id) {
                 // Update the task item with the backend task ID and initial status
                 setTasks(prevTasks => prevTasks.map(task =>
                     task.id === taskId ? { ...task, backendTaskId: responseData.task_id, status: responseData.status || 'queued', uploadProgress: 100 } : task
                 ));
                 // Optionally, start polling for this task's status
                 // startPollingStatus(responseData.task_id); // We will implement polling later
            } else {
                 // Handle unexpected response format from backend
                 throw new Error("Invalid response from server.");
            }

        } catch (error) {
            console.error("Upload failed:", error);
            // Update task status to failed
             setTasks(prevTasks => prevTasks.map(task =>
                 task.id === taskId ? { ...task, status: 'failed', error: error.message || 'Upload failed' } : task
             ));
             alert(`Upload failed: ${error.message || 'Unknown error'}`);
        } finally {
            setIsLoading(false); // End loading
            setSelectedFile(null); // Clear selected file after attempt
            setUploadProgress(0); // Reset progress
        }
    };

    // --- Task Status Polling Logic ---
    // This could be a useEffect hook or a separate function/hook
    // Polling should check status for tasks that are not yet completed or failed
    useEffect(() => {
        // Start polling when component mounts or tasks state changes
        const pollingInterval = setInterval(() => {
            const activeTasks = tasks.filter(task =>
                task.backendTaskId && (task.status === 'queued' || task.status === 'processing')
            );

            activeTasks.forEach(async (task) => {
                try {
                    // Call API service to get task status
                    const statusResponse = await apiService.getTaskStatus(task.backendTaskId);
                    if (statusResponse && statusResponse.status) {
                        // Update the task item's status and other info
                        setTasks(prevTasks => prevTasks.map(t =>
                            t.id === task.id ? { ...t, status: statusResponse.status, result: statusResponse } : t // Store status response in result for now
                        ));
                        // If status is completed or failed, stop polling for this task (handled by the filter in the next interval)
                        if (statusResponse.status === 'completed' || statusResponse.status === 'failed') {
                            logger.info(`Polling stopped for task ${task.backendTaskId}. Status: ${statusResponse.status}`);
                            // If completed, might fetch detailed results immediately
                             if (statusResponse.status === 'completed') {
                                logger.info(`Workspaceing detailed results for task ${task.backendTaskId}.`);
                                const detailedResult = await apiService.getTaskResult(task.backendTaskId);
                                setTasks(prevTasks => prevTasks.map(t =>
                                     t.id === task.id ? { ...t, result: detailedResult } : t // Overwrite with detailed result
                                ));
                             }
                        }
                    }
                } catch (error) {
                    console.error(`Error polling status for task ${task.backendTaskId}:`, error);
                    // Optionally mark task as errored in the UI if polling fails repeatedly
                     setTasks(prevTasks => prevTasks.map(t =>
                         t.id === task.id ? { ...t, status: 'polling_error', error: error.message || 'Polling failed' } : t
                     ));
                }
            });

            // Note: This simple polling polls ALL active tasks in every interval.
            // For many tasks, optimize by polling less frequently or staggering requests.

        }, 5000); // Poll every 5 seconds (adjust as needed)

        // Clean up the interval when the component unmounts or dependencies change
        return () => clearInterval(pollingInterval);
    }, [tasks]); // Dependency array: Restart effect if 'tasks' list changes

    // --- Result Display Logic ---
    const handleViewResults = (taskId) => {
        setSelectedTask(taskId); // Set the task ID to view details
    };

    const handleCloseDetails = () => {
        setSelectedTask(null); // Close the details view
    };

    // Find the task object for the details view
    const taskDetails = tasks.find(task => task.id === selectedTask);


    // --- Render UI ---
    return (
        <div className="app-container">
            <Header />
            <h1>Personal Data Assistant - Music Score Conversion</h1>

            <FileUploader
                onFileSelect={handleFileSelect}
                onUpload={handleUpload}
                selectedFile={selectedFile}
                uploadProgress={uploadProgress}
                isLoading={isLoading}
            />

            {/* Show task list and potentially progress/status */}
            <TaskList tasks={tasks} onViewResults={handleViewResults} />

            {/* Show task details or results if a task is selected */}
            {selectedTask && taskDetails && (
                <TaskDetails task={taskDetails} onClose={handleCloseDetails} />
            )}

            {/* Optional: Global loading indicator */}
            {/* {isLoading && <div className="loading-indicator">Processing...</div>} */}
        </div>
    );
}

export default App;
