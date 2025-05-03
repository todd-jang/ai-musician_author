// frontend/src/components/FileUploader.jsx

import React, { useRef } from 'react';

function FileUploader({ onFileSelect, onUpload, selectedFile, uploadProgress, isLoading }) {
    const fileInputRef = useRef(null);

    const handleButtonClick = () => {
        // Trigger the hidden file input click
        fileInputRef.current.click();
    };

    const handleFileChange = (event) => {
        const file = event.target.files ? event.target.files[0] : null;
        if (file) {
            onFileSelect(file);
        }
        // Clear the input value so the same file can be selected again after upload
        event.target.value = null;
    };

    const handleUploadClick = () => {
        onUpload();
    };

    return (
        <div className="file-uploader">
            <h2>Upload Your Music Score</h2>
            <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }} // Hide the default input
                onChange={handleFileChange}
                accept=".pdf,.xml,.mxl,.musicxml,.midi" // Specify accepted file types
            />
            <button onClick={handleButtonClick} disabled={isLoading}>
                {selectedFile ? selectedFile.name : "Select File"}
            </button>

            {selectedFile && (
                <div className="upload-controls">
                    <button onClick={handleUploadClick} disabled={isLoading}>
                        {isLoading ? "Uploading..." : "Upload"}
                    </button>
                    {uploadProgress > 0 && uploadProgress <= 100 && (
                        <div className="progress-bar-container">
                            <div
                                className="progress-bar"
                                style={{ width: `${uploadProgress}%` }}
                            >
                                {uploadProgress.toFixed(0)}%
                            </div>
                        </div>
                    )}
                </div>
            )}

            {isLoading && <p>Processing...</p>} {/* Or a more sophisticated loader */}
        </div>
    );
}

export default FileUploader;
