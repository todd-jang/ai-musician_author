// frontend/tests/__tests__/components/TaskDetails.test.js

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TaskDetails from '../../../src/components/TaskDetails';
import { act } from 'react-dom/test-utils'; // Import act for state updates

// Mock the child components if they were complex (e.g., MusicPlayer, TranslationDisplay)
// jest.mock('../../../src/components/MusicPlayer', () => ({ src }) => <audio data-testid="music-player" src={src} controls />);
// jest.mock('../../../src/components/TranslationDisplay', () => ({ text }) => <div data-testid="translation-display">{text}</div>);

describe('TaskDetails', () => {
    const mockOnClose = jest.fn();

    // Helper to render the component
    const renderComponent = (props) => {
        const defaultTask = { // Basic structure mirroring App.jsx state and db_service result
             id: 'task-123',
             filename: 'test_file.pdf',
             status: 'completed', // TaskDetails typically shown for completed/errored
             result: null, // Result from task_results table (detailed_results JSONB)
             error: null
        };
        const mergedTask = { ...defaultTask, ...props.task };
        render(<TaskDetails task={mergedTask} onClose={mockOnClose} />);
    };

    beforeEach(() => {
        mockOnClose.mockClear();
    });

    test('renders loading state if result is null', () => {
        renderComponent({ task: { result: null } });

        expect(screen.getByText(/Loading or no result data available/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Close/i })).toBeInTheDocument();
    });

    test('renders completed task details with processing time', () => {
        const taskWithResult = {
            status: 'completed',
            result: {
                final_status: 'completed',
                processing_time_seconds: 45.67,
                detailed_results: {}, // Empty detailed results for this test
                completed_at: new Date().toISOString()
            }
        };
        renderComponent({ task: taskWithResult });

        expect(screen.getByText(/Results for Task: test_file.pdf/i)).toBeInTheDocument();
        expect(screen.getByText(/Status: Completed/i)).toBeInTheDocument();
        expect(screen.getByText(/Processing Time: 45.67s/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Close/i })).toBeInTheDocument();
        // Ensure result-specific sections are not rendered if detailed_results is empty
        expect(screen.queryByText(/Shakespearean Translation:/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Generated Music:/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Analysis Summary:/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Error:/i)).not.toBeInTheDocument();
    });

    test('renders translated text result', () => {
        const taskWithTranslation = {
            status: 'completed',
            result: {
                 final_status: 'completed',
                 processing_time_seconds: 20,
                 detailed_results: {
                      shakespearean_translation: {
                           status: 'success',
                           translated: 'Hark! A most melodious tune!'
                      }
                 },
                 completed_at: new Date().toISOString()
            }
        };
        renderComponent({ task: taskWithTranslation });

        expect(screen.getByText(/Shakespearean Translation:/i)).toBeInTheDocument();
        expect(screen.getByText(/Hark! A most melodious tune!/i)).toBeInTheDocument();
    });

    test('renders music file location (S3 key)', () => {
        const taskWithMusic = {
             status: 'completed',
             result: {
                  final_status: 'completed',
                  processing_time_seconds: 30,
                  detailed_results: {
                       generated_music_file: {
                            status: 'success',
                            s3_key: 'results/task-123/output.mp3'
                       }
                  },
                 completed_at: new Date().toISOString()
             }
        };
        renderComponent({ task: taskWithMusic });

        expect(screen.getByText(/Generated Music:/i)).toBeInTheDocument();
        expect(screen.getByText(/File Location: results\/task-123\/output.mp3/i)).toBeInTheDocument();
        // Check if audio tag is rendered ONLY if URL is available (based on component logic)
        expect(screen.queryByTestId('music-player')).not.toBeInTheDocument();
    });

     test('renders music file location (HTTP URL) and audio player', () => {
         const taskWithMusicUrl = {
              status: 'completed',
              result: {
                   final_status: 'completed',
                   processing_time_seconds: 30,
                   detailed_results: {
                        generated_music_file: {
                             status: 'success',
                             url: 'http://example.com/results/task-123/output.mp3' # Use 'url' field
                        }
                   },
                  completed_at: new Date().toISOString()
              }
         };
         renderComponent({ task: taskWithMusicUrl });

         expect(screen.getByText(/Generated Music:/i)).toBeInTheDocument();
         expect(screen.getByText(/File Location: http:\/\/example.com\/results\/task-123\/output.mp3/i)).toBeInTheDocument();

         // Check if a basic audio tag is rendered using the URL
         const audioPlayer = screen.getByTestId('audio-player'); // Add data-testid="audio-player" to the <audio> tag
         expect(audioPlayer).toBeInTheDocument();
         expect(audioPlayer).toHaveAttribute('src', 'http://example.com/results/task-123/output.mp3');

     });


    test('renders analysis summary (JSON)', () => {
        const taskWithAnalysis = {
             status: 'completed',
             result: {
                  final_status: 'completed',
                  processing_time_seconds: 40,
                  detailed_results: {
                       analysis_summary: {
                            tempo: 120,
                            key_signature: "C Major"
                       }
                  },
                  completed_at: new Date().toISOString()
             }
        };
        renderComponent({ task: taskWithAnalysis });

        expect(screen.getByText(/Analysis Summary:/i)).toBeInTheDocument();
        // Check if the stringified JSON is displayed
        expect(screen.getByText(/{"tempo": 120,/i)).toBeInTheDocument(); // Check part of the JSON string
        expect(screen.getByText(/"key_signature": "C Major"}/i)).toBeInTheDocument();
    });

    test('renders failed task details with error message', () => {
         const taskFailed = {
              status: 'failed',
              error: 'Processing failed due to invalid file.',
              result: { // result might still exist with partial info or error details
                   final_status: 'failed',
                   processing_time_seconds: 10,
                   detailed_results: { error_step: 'OMR' },
                   completed_at: new Date().toISOString()
              }
         };
         renderComponent({ task: taskFailed });

         expect(screen.getByText(/Status: Failed/i)).toBeInTheDocument();
         expect(screen.getByText(/Error:/i)).toBeInTheDocument();
         expect(screen.getByText(/Processing failed due to invalid file./i)).toBeInTheDocument();
         expect(screen.queryByText(/Translation:/i)).not.toBeInTheDocument(); // Ensure success-only sections are hidden
     });

    test('calls onClose when close button is clicked', () => {
        renderComponent({ task: { status: 'completed', result: {} } }); // Render with a minimal result to show close button

        const closeButton = screen.getByRole('button', { name: /Close/i });
        fireEvent.click(closeButton);

        // Assert that the onClose callback was called
        expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

});

// --- Update frontend/src/components/TaskDetails.jsx to add data-testid for audio ---
// Find this line:
// <audio controls src={musicFileLocation}>
// Change it to:
// <audio data-testid="audio-player" controls src={musicFileLocation}>
