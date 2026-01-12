'use client';

import { useEffect, useState } from 'react';
import Card from '../UI/Card';

interface SystemStats {
  tasksRunning: number;
  totalTasks: number;
  agentsActive: number;
  systemHealth: string;
}

export default function OverviewCards() {
  const [stats, setStats] = useState<SystemStats>({
    tasksRunning: 0,
    totalTasks: 0,
    agentsActive: 0,
    systemHealth: 'Loading...'
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      // Fetch task stats
      const taskResponse = await fetch('/api/scheduler/tasks');
      const tasks = taskResponse.ok ? await taskResponse.json() : [];

      // Fetch agent stats
      const agentResponse = await fetch('/api/agents/');
      const agents = agentResponse.ok ? await agentResponse.json() : [];

      // Fetch health status
      const healthResponse = await fetch('/api/health/ready');
      const health = healthResponse.ok ? 'Healthy' : 'Issues';

      setStats({
        tasksRunning: tasks.filter((t: any) => t.is_active).length,
        totalTasks: tasks.length,
        agentsActive: agents.length,
        systemHealth: health
      });
    } catch (error) {
      console.error('Error fetching stats:', error);
      setStats(prev => ({ ...prev, systemHealth: 'Error' }));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="grid md:grid-cols-4 gap-6 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="bg-gray-200 h-24 rounded-lg"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid md:grid-cols-4 gap-6 mb-6">
      <Card
        title="System Health"
        value={stats.systemHealth}
        className={stats.systemHealth === 'Healthy' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}
      />
      <Card
        title="Active AI Tasks"
        value={`${stats.tasksRunning} Running`}
        subtitle={`${stats.totalTasks} Total`}
      />
      <Card
        title="Available Agents"
        value={`${stats.agentsActive} Agents`}
        subtitle="Finance, News, Research"
      />
      <Card
        title="Recent Activity"
        value="Real-time"
        subtitle="Live monitoring active"
      />
    </div>
  );
}

