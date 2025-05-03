// frontend/src/components/TaskItem.jsx

import React from 'react';

function TaskItem({ task, onViewResults }) {
    // Determine status display and actions based on task status
    const getStatusDisplay = (status) => {
        switch (status) {
            case 'uploading':
                return `Uploading... (${task.uploadProgress}%)`;
            case 'processing_queued':
            case 'queued':
                return 'Queued';
            case 'processing':
                return 'Processing...';
            case 'completed':
                return 'Completed';
            case 'completed_with_errors':
                return 'Completed with Errors';
            case 'failed':
                return `Failed: ${task.error || 'Unknown Error'}`;
            case 'polling_error':
                 return `Error polling status: ${task.error || 'Unknown Error'}`;
            default:
                return 'Unknown Status';
        }
    };

    const handleViewResultsClick = () => {
        if (task.status === 'completed' || task.status === 'completed_with_errors') {
            onViewResults(task.id);
        }
    };


    return (
        <li className={`task-item status-${task.status}`}>
            <span>File: {task.filename}</span>
            <span>Status: {getStatusDisplay(task.status)}</span>
            {/* Button to view results, only active for completed tasks */}
            {(task.status === 'completed' || task.status === 'completed_with_errors') && (
                <button onClick={handleViewResultsClick}>View Results</button>
            )}
             {/* Optional: Show a retry button for failed tasks */}
             {/* {task.status === 'failed' && (
                 <button onClick={() => {/* retry logic */}>Retry</button>
             )} */}
        </li>
    );
}

export default TaskItem;
