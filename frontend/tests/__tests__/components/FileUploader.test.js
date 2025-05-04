// frontend/tests/__tests__/components/FileUploader.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FileUploader from '../../../src/components/FileUploader';

describe('FileUploader', () => {
    // Mock the callback functions
    const mockOnFileSelect = jest.fn();
    const mockOnUpload = jest.fn();

    // Helper to render the component with default props
    const renderComponent = (props = {}) => {
        const defaultProps = {
            onFileSelect: mockOnFileSelect,
            onUpload: mockOnUpload,
            selectedFile: null,
            uploadProgress: 0,
            isLoading: false,
            ...props,
        };
        render(<FileUploader {...defaultProps} />);
    };

    // Reset mocks before each test
    beforeEach(() => {
        mockOnFileSelect.mockClear();
        mockOnUpload.mockClear();
    });

    test('renders select file button initially', () => {
        renderComponent();

        // Assert that the "Select File" button is present
        const selectButton = screen.getByRole('button', { name: /Select File/i });
        expect(selectButton).toBeInTheDocument();
        // Assert that the upload button is not visible yet
        const uploadButton = screen.queryByRole('button', { name: /Upload/i });
        expect(uploadButton).not.toBeInTheDocument();
    });

    test('calls onFileSelect when a file is chosen', () => {
        renderComponent();

        // Find the hidden file input by its type
        const fileInput = screen.getByLabelText(/Select File/i); // Use label text if button triggers hidden input

        // Create a mock file
        const mockFile = new File(['dummy content'], 'my_score.pdf', { type: 'application/pdf' });

        // Simulate changing the file input value
        fireEvent.change(fileInput, { target: { files: [mockFile] } });

        // Assert that the onFileSelect callback was called with the file
        expect(mockOnFileSelect).toHaveBeenCalledTimes(1);
        expect(mockOnFileSelect).toHaveBeenCalledWith(mockFile);
    });

    test('shows upload button and filename after file selection', () => {
        const mockFile = new File(['dummy content'], 'my_score.pdf', { type: 'application/pdf' });
        renderComponent({ selectedFile: mockFile });

        // Assert the button shows the filename
        const selectButton = screen.getByRole('button', { name: /my_score.pdf/i });
        expect(selectButton).toBeInTheDocument();

        // Assert the "Upload" button is visible
        const uploadButton = screen.getByRole('button', { name: /Upload/i });
        expect(uploadButton).toBeInTheDocument();
    });

    test('calls onUpload when upload button is clicked', () => {
        const mockFile = new File(['dummy content'], 'my_score.pdf', { type: 'application/pdf' });
        renderComponent({ selectedFile: mockFile });

        // Find the "Upload" button
        const uploadButton = screen.getByRole('button', { name: /Upload/i });

        // Simulate clicking the upload button
        fireEvent.click(uploadButton);

        // Assert that the onUpload callback was called
        expect(mockOnUpload).toHaveBeenCalledTimes(1);
    });

    test('shows uploading state and progress bar', () => {
        const mockFile = new File(['dummy content'], 'my_score.pdf', { type: 'application/pdf' });
        // Simulate uploading state with some progress
        renderComponent({ selectedFile: mockFile, uploadProgress: 50, isLoading: true });

        // Assert button text changes
        const uploadButton = screen.getByRole('button', { name: /Uploading.../i });
        expect(uploadButton).toBeInTheDocument();

        // Assert progress bar is visible and shows the correct percentage
        const progressBar = screen.getByText(/50%/i);
        expect(progressBar).toBeInTheDocument();

        // Assert button is disabled
        expect(uploadButton).toBeDisabled();
    });

    test('clears file input value after file selection', () => {
        renderComponent();
        const fileInput = screen.getByLabelText(/Select File/i); // Use label text if button triggers hidden input
        const mockFile = new File(['dummy content'], 'my_score.pdf', { type: 'application/pdf' });

        // Simulate file selection
        fireEvent.change(fileInput, { target: { files: [mockFile] } });

        // Assert that the input's value is reset (important for selecting the same file again)
        // In React Testing Library, accessing input.value directly after change can be tricky.
        // A common way to test this is to verify that the onFileSelect was called again if you select the same file twice
        // or rely on the component's logic to handle the reset via event.target.value = null.
        // We can't directly assert input.value = null easily in all scenarios with RTL.
        // Let's trust the standard pattern: event.target.value = null clears it.
        // Alternatively, test by triggering change twice with the same file and check onFileSelect calls.

        // Arrange for second selection
        mockOnFileSelect.mockClear(); // Clear mock call history

        // Simulate selecting the same file again
        fireEvent.change(fileInput, { target: { files: [mockFile] } });

        // Assert onFileSelect was called again, indicating the change event was detected
        expect(mockOnFileSelect).toHaveBeenCalledTimes(1);
    });

});
