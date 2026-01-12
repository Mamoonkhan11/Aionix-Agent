'use client';

import { useState } from 'react';
import Card from '../UI/Card';
import Button from '../UI/Button';
import Input from '../UI/Input';

interface TaskFormData {
  name: string;
  description: string;
  task_type: string;
  frequency: string;
  schedule_time: string;
  query: string; // For web search tasks
  max_results: number;
}

export default function TaskRequestForm() {
  const [form, setForm] = useState<TaskFormData>({
    name: '',
    description: '',
    task_type: 'web_search',
    frequency: 'daily',
    schedule_time: '09:00',
    query: '',
    max_results: 10
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setSuccess(false);

    try {
      // Prepare task configuration based on type
      let taskConfig: any = {};

      if (form.task_type === 'web_search') {
        taskConfig = {
          query: form.query,
          max_results: form.max_results,
          search_type: 'general'
        };
      }

      const taskData = {
        name: form.name,
        description: form.description,
        task_type: form.task_type,
        frequency: form.frequency,
        task_config: taskConfig,
        schedule_time: form.frequency !== 'minutely' && form.frequency !== 'hourly' ? form.schedule_time : undefined,
        is_shared: false
      };

      const response = await fetch('/api/scheduler/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskData),
      });

      if (response.ok) {
        const result = await response.json();
        setSuccess(true);
        // Reset form
        setForm({
          name: '',
          description: '',
          task_type: 'web_search',
          frequency: 'daily',
          schedule_time: '09:00',
          query: '',
          max_results: 10
        });
        // Trigger page refresh to show new task
        window.location.reload();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create task');
      }
    } catch (error) {
      console.error('Error creating task:', error);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Create Scheduled Task">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Task Name *
            </label>
            <Input
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="e.g., Daily Market Research"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Task Type
            </label>
            <select
              name="task_type"
              value={form.task_type}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="web_search">Web Search</option>
              <option value="data_analysis">Data Analysis</option>
              <option value="report_generation">Report Generation</option>
              <option value="agent_interaction">Agent Interaction</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            name="description"
            value={form.description}
            onChange={handleChange}
            placeholder="Describe what this task does..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Frequency
            </label>
            <select
              name="frequency"
              value={form.frequency}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="hourly">Hourly</option>
              <option value="minutely">Every Minute (Testing)</option>
            </select>
          </div>

          {(form.frequency === 'daily' || form.frequency === 'weekly') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Schedule Time
              </label>
              <Input
                type="time"
                name="schedule_time"
                value={form.schedule_time}
                onChange={handleChange}
                required
              />
            </div>
          )}
        </div>

        {form.task_type === 'web_search' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search Query *
              </label>
              <Input
                name="query"
                value={form.query}
                onChange={handleChange}
                placeholder="What to search for..."
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Results
              </label>
              <select
                name="max_results"
                value={form.max_results}
                onChange={(e) => setForm(prev => ({ ...prev, max_results: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={5}>5 results</option>
                <option value={10}>10 results</option>
                <option value={20}>20 results</option>
                <option value={50}>50 results</option>
              </select>
            </div>
          </div>
        )}

        {error && (
          <div className="text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
            {error}
          </div>
        )}

        {success && (
          <div className="text-green-600 bg-green-50 border border-green-200 rounded-md p-3">
            Task created successfully!
          </div>
        )}

        <div className="flex justify-end space-x-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => setForm({
              name: '',
              description: '',
              task_type: 'web_search',
              frequency: 'daily',
              schedule_time: '09:00',
              query: '',
              max_results: 10
            })}
          >
            Reset
          </Button>
          <Button type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Task'}
          </Button>
        </div>
      </form>
    </Card>
  );
}

