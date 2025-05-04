// frontend/tests/__tests__/components/TaskItem.test.js

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TaskItem from '../../../src/components/TaskItem';

describe('TaskItem', () => {
    // Mock the callback function
    const mockOnViewResults = jest.fn();

    // Helper to render the component with default props
    const renderComponent = (props) => {
        const defaultTask = {
            id: 'task-123',
            filename: 'test_score.pdf',
            status: 'queued',
            uploadProgress: 0,
            result: null,
            error: null
        };
        const mergedTask = { ...defaultTask, ...props.task };
        const defaultProps = {
            task: mergedTask,
            onViewResults: mockOnViewResults,
            ...props
        };
        render(<TaskItem {...defaultProps} />);
    };

    // Reset mocks before each test
    beforeEach(() => {
        mockOnViewResults.mockClear();
    });

    test('renders task filename and status', () => {
        renderComponent({ task: { filename: 'my_file.musicxml', status: 'processing' } });

        expect(screen.getByText(/my_file.musicxml/i)).toBeInTheDocument();
        expect(screen.getByText(/Processing.../i)).toBeInTheDocument();
    });

    test('shows "Queued" status correctly', () => {
        renderComponent({ task: { status: 'queued' } });
        expect(screen.getByText(/Queued/i)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /View Results/i })).not.toBeInTheDocument();
    });

    test('shows "Uploading" status with progress', () => {
        renderComponent({ task: { status: 'uploading', uploadProgress: 75 } });
        expect(screen.getByText(/Uploading... \(75%\)/i)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /View Results/i })).not.toBeInTheDocument();
    });

    test('shows "Completed" status and view results button', () => {
        renderComponent({ task: { status: 'completed' } });
        expect(screen.getByText(/Completed/i)).toBeInTheDocument();
        const viewResultsButton = screen.getByRole('button', { name: /View Results/i });
        expect(viewResultsButton).toBeInTheDocument();
        expect(viewResultsButton).toBeEnabled(); // Button should be clickable
    });

     test('shows "Completed with Errors" status and view results button', () => {
        renderComponent({ task: { status: 'completed_with_errors' } });
        expect(screen.getByText(/Completed with Errors/i)).toBeInTheDocument();
        const viewResultsButton = screen.getByRole('button', { name: /View Results/i });
        expect(viewResultsButton).toBeInTheDocument();
        expect(viewResultsButton).toBeEnabled(); // Button should be clickable
    });


    test('shows "Failed" status with error message', () => {
        renderComponent({ task: { status: 'failed', error: 'Processing failed' } });
        expect(screen.getByText(/Failed: Processing failed/i)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /View Results/i })).not.toBeInTheDocument();
    });

    test('calls onViewResults when view results button is clicked for completed task', () => {
        const task = { id: 'task-456', filename: 'completed.pdf', status: 'completed' };
        renderComponent({ task });

        const viewResultsButton = screen.getByRole('button', { name: /View Results/i });
        fireEvent.click(viewResultsButton);

        // Assert that the onViewResults callback was called with the task ID
        expect(mockOnViewResults).toHaveBeenCalledTimes(1);
        expect(mockOnViewResults).toHaveBeenCalledWith(task.id);
    });

    test('does not call onViewResults when view results button is clicked for non-completed task', () => {
         const task = { id: 'task-789', filename: 'processing.pdf', status: 'processing' };
         renderComponent({ task });

         const viewResultsButton = screen.queryByRole('button', { name: /View Results/i });
         expect(viewResultsButton).not.toBeInTheDocument(); // Button should not even be present

         // If the button were present but disabled, we'd check isabled state.
         // In our component logic, it's only rendered for 'completed'/'completed_with_errors'.

         // Just to be safe, if somehow a button appeared, clicking it shouldn't trigger the mock
         if(viewResultsButton) {
             fireEvent.click(viewResultsButton);
             expect(mockOnViewResults).not.toHaveBeenCalled();
         }
    });

});
