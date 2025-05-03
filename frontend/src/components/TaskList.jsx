// frontend/src/components/TaskList.jsx

import React from 'react';
import TaskItem from './TaskItem';

function TaskList({ tasks, onViewResults }) {
    if (tasks.length === 0) {
        return <div className="task-list"><p>No tasks initiated yet.</p></div>;
    }

    return (
        <div className="task-list">
            <h2>Your Tasks</h2>
            <ul>
                {tasks.map(task => (
                    <TaskItem key={task.id} task={task} onViewResults={onViewResults} />
                ))}
            </ul>
        </div>
    );
}

export default TaskList;
