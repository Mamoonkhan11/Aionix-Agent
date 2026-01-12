'use client';

import { useEffect, useState } from 'react';
import Card from '../UI/Card';
import Button from '../UI/Button';

interface ScheduledTask {
  id: string;
  name: string;
  task_type: string;
  frequency: string;
  is_active: boolean;
  last_run: string | null;
  next_run: string | null;
  created_at: string;
}

export default function TaskQueue() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch('/api/scheduler/tasks');
      if (response.ok) {
        const data = await response.json();
        setTasks(data);
      } else {
        setError('Failed to load tasks');
      }
    } catch (error) {
      console.error('Error fetching tasks:', error);
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  const executeTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/scheduler/tasks/${taskId}/execute`, {
        method: 'POST',
      });

      if (response.ok) {
        alert('Task execution queued successfully!');
        fetchTasks(); // Refresh the list
      } else {
        alert('Failed to execute task');
      }
    } catch (error) {
      console.error('Error executing task:', error);
      alert('Network error');
    }
  };

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const getStatusBadge = (isActive: boolean, nextRun: string | null) => {
    if (!isActive) return <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded">Inactive</span>;
    if (!nextRun) return <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">Pending</span>;
    return <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">Scheduled</span>;
  };

  if (loading) {
    return (
      <div className="my-8">
        <h2 className="text-lg font-semibold mb-4">Task Queue</h2>
        <div className="animate-pulse space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="my-8">
        <h2 className="text-lg font-semibold mb-4">Task Queue</h2>
        <div className="text-red-600 p-4">
          <p>Error loading tasks: {error}</p>
          <Button onClick={fetchTasks} className="mt-2">Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="my-8">
      <h2 className="text-lg font-semibold mb-4">Task Queue</h2>
      <div className="space-y-4">
        {tasks.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No scheduled tasks found.</p>
        ) : (
          tasks.map((task) => (
            <div key={task.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="font-semibold text-gray-900">{task.name}</h3>
                  <p className="text-sm text-gray-600 capitalize">{task.task_type.replace('_', ' ')}</p>
                </div>
                <div className="flex items-center space-x-2">
                  {getStatusBadge(task.is_active, task.next_run)}
                  <Button
                    onClick={() => executeTask(task.id)}
                    size="sm"
                    className="text-xs"
                  >
                    Execute Now
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Frequency:</span>
                  <span className="ml-2 capitalize">{task.frequency}</span>
                </div>
                <div>
                  <span className="text-gray-500">Last Run:</span>
                  <span className="ml-2">{formatDateTime(task.last_run)}</span>
                </div>
                <div className="col-span-2">
                  <span className="text-gray-500">Next Run:</span>
                  <span className="ml-2">{formatDateTime(task.next_run)}</span>
                </div>
              </div>
            </div>
          ))
        )}

        <div className="pt-4 border-t">
          <Button onClick={fetchTasks} variant="outline" size="sm">
            Refresh Tasks
          </Button>
        </div>
      </div>
    </div>
  );
}

