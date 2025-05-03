// frontend/src/components/TaskDetails.jsx

import React from 'react';
// Import components for displaying results (e.g., MusicPlayer, TranslationDisplay)
// import MusicPlayer from './MusicPlayer'; // Need to create
// import TranslationDisplay from './TranslationDisplay'; // Need to create

function TaskDetails({ task, onClose }) {
    if (!task || !task.result) {
        return (
             <div className="task-details-overlay">
                 <div className="task-details-content">
                      <h2>Task Details</h2>
                      <p>Loading or no result data available for task {task?.filename || task?.id}...</p>
                      <button onClick={onClose}>Close</button>
                 </div>
             </div>
        );
    }

    // Access detailed results from the task object
    // The structure of task.result depends on the detailed_results JSONB from the backend
    const detailedResults = task.result.detailed_results || {};
    const musicFileLocation = detailedResults.generated_music_file?.s3_key || detailedResults.generated_music_file?.url; // Assuming S3 key or URL
    const translatedText = detailedResults.shakespearean_translation?.translated;
    const analysisSummary = detailedResults.analysis_summary;


    return (
        <div className="task-details-overlay"> {/* Use overlay for modal-like view */}
            <div className="task-details-content">
                <h2>Results for Task: {task.filename}</h2>
                <p>Status: {task.status}</p>
                <p>Processing Time: {task.result.processing_time_seconds?.toFixed(2) || 'N/A'}s</p>

                {/* Display Translated Text */}
                {translatedText && (
                    <div>
                        <h3>Shakespearean Translation:</h3>
                        {/* <TranslationDisplay text={translatedText} /> */}
                         <p>{translatedText}</p> {/* Simple text display */}
                    </div>
                )}

                {/* Display Music Player */}
                {musicFileLocation && (
                    <div>
                        <h3>Generated Music:</h3>
                        <p>File Location: {musicFileLocation}</p>
                        {/* Use an audio player component */}
                        {/* <MusicPlayer url={musicFileLocation} /> */}
                        {/* Simple HTML audio tag example (requires direct URL access) */}
                        {musicFileLocation.startsWith('http') && (
                             <audio controls src={musicFileLocation}>
                                 Your browser does not support the audio element.
                             </audio>
                        )}
                         {/* If S3 key is returned, need a way to get a temporary public URL */}
                         {/* This might involve another backend API call */}
                    </div>
                )}

                {/* Display Analysis Summary */}
                {analysisSummary && (
                    <div>
                        <h3>Analysis Summary:</h3>
                        <pre>{JSON.stringify(analysisSummary, null, 2)}</pre> {/* Display JSON structure */}
                    </div>
                )}

                {/* Display Error Information if failed */}
                {task.status === 'failed' && task.error && (
                     <div style={{color: 'red'}}>
                         <h3>Error:</h3>
                         <p>{task.error}</p>
                     </div>
                )}
                {task.status === 'completed_with_errors' && (
                     <div style={{color: 'orange'}}>
                         <h3>Warning / Partial Errors:</h3>
                         <p>{task.error || 'Task completed with some errors.'}</p>
                         {/* Could display specific step errors from detailedResults */}
                     </div>
                )}


                <button onClick={onClose}>Close</button>
            </div>
        </div>
    );
}

export default TaskDetails;
