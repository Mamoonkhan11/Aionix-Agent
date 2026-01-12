'use client';

import { useEffect, useState } from 'react';
import Card from '../UI/Card';
import Button from '../UI/Button';
import Input from '../UI/Input';

interface Agent {
  name: string;
  class_name: string;
  description: string;
  capabilities: string[];
  module: string;
}

interface AgentResponse {
  success: boolean;
  response: string;
  data: any;
  actions_taken: string[];
  confidence_score: number;
  reasoning_steps: string[];
  execution_time: number;
}

export default function AgentInteraction() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(true);

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await fetch('/api/agents/');
      if (response.ok) {
        const data = await response.json();
        setAgents(data);
        if (data.length > 0) {
          setSelectedAgent(data[0].name);
        }
      }
    } catch (error) {
      console.error('Error fetching agents:', error);
    } finally {
      setLoadingAgents(false);
    }
  };

  const executeAgent = async () => {
    if (!selectedAgent || !query.trim()) return;

    setLoading(true);
    setResponse(null);

    try {
      const response = await fetch(`/api/agents/${selectedAgent}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim()
        }),
      });

      const result = await response.json();

      if (response.ok) {
        setResponse(result);
      } else {
        setResponse({
          success: false,
          response: result.detail || 'Agent execution failed',
          data: {},
          actions_taken: [],
          confidence_score: 0,
          reasoning_steps: [],
          execution_time: 0
        });
      }
    } catch (error) {
      console.error('Error executing agent:', error);
      setResponse({
        success: false,
        response: 'Network error occurred',
        data: {},
        actions_taken: [],
        confidence_score: 0,
        reasoning_steps: [],
        execution_time: 0
      });
    } finally {
      setLoading(false);
    }
  };

  const getCapabilityColor = (capability: string) => {
    const colors: Record<string, string> = {
      finance: 'bg-green-100 text-green-800',
      news: 'bg-blue-100 text-blue-800',
      research: 'bg-purple-100 text-purple-800',
      analysis: 'bg-yellow-100 text-yellow-800',
      search: 'bg-indigo-100 text-indigo-800',
      default: 'bg-gray-100 text-gray-800'
    };

    const key = Object.keys(colors).find(k => capability.toLowerCase().includes(k)) || 'default';
    return colors[key];
  };

  if (loadingAgents) {
    return (
      <div className="space-y-6">
        <Card title="Available Agents">
          <div className="animate-pulse space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Agent Selection */}
      <Card title="Available Agents">
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <div
              key={agent.name}
              className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                selectedAgent === agent.name
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setSelectedAgent(agent.name)}
            >
              <h3 className="font-semibold text-gray-900 mb-1">{agent.name}</h3>
              <p className="text-sm text-gray-600 mb-2">{agent.description}</p>
              <div className="flex flex-wrap gap-1">
                {agent.capabilities.slice(0, 3).map((capability) => (
                  <span
                    key={capability}
                    className={`px-2 py-1 text-xs rounded ${getCapabilityColor(capability)}`}
                  >
                    {capability}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Agent Interaction */}
      <Card title="Agent Interaction">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Selected Agent: {selectedAgent || 'None selected'}
            </label>
            <div className="flex space-x-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your query or task..."
                className="flex-1"
                onKeyPress={(e) => e.key === 'Enter' && executeAgent()}
              />
              <Button
                onClick={executeAgent}
                disabled={!selectedAgent || !query.trim() || loading}
              >
                {loading ? 'Processing...' : 'Execute'}
              </Button>
            </div>
          </div>

          {/* Response Display */}
          {response && (
            <div className={`p-4 rounded-lg border ${
              response.success
                ? 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <h3 className={`font-semibold ${
                  response.success ? 'text-green-800' : 'text-red-800'
                }`}>
                  Agent Response
                </h3>
                <div className="text-sm text-gray-600">
                  Confidence: {(response.confidence_score * 100).toFixed(1)}% |
                  Time: {response.execution_time.toFixed(2)}s
                </div>
              </div>

              <div className="prose prose-sm max-w-none">
                <div className="whitespace-pre-wrap text-gray-700">
                  {response.response}
                </div>
              </div>

              {response.actions_taken.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Actions Taken:</h4>
                  <ul className="text-sm text-gray-600 list-disc list-inside">
                    {response.actions_taken.map((action, i) => (
                      <li key={i}>{action}</li>
                    ))}
                  </ul>
                </div>
              )}

              {response.reasoning_steps.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Reasoning Steps:</h4>
                  <ol className="text-sm text-gray-600 list-decimal list-inside">
                    {response.reasoning_steps.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Quick Actions */}
      <Card title="Quick Actions">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Button
            onClick={() => setQuery("Analyze the current stock market trends")}
            variant="outline"
            className="h-auto p-4 flex flex-col items-center"
          >
            <span className="text-sm font-medium">Market Analysis</span>
            <span className="text-xs text-gray-500 mt-1">Stock trends</span>
          </Button>

          <Button
            onClick={() => setQuery("Search for recent AI developments")}
            variant="outline"
            className="h-auto p-4 flex flex-col items-center"
          >
            <span className="text-sm font-medium">AI News</span>
            <span className="text-xs text-gray-500 mt-1">Latest updates</span>
          </Button>

          <Button
            onClick={() => setQuery("Research sustainable investing strategies")}
            variant="outline"
            className="h-auto p-4 flex flex-col items-center"
          >
            <span className="text-sm font-medium">Investment Research</span>
            <span className="text-xs text-gray-500 mt-1">ESG strategies</span>
          </Button>

          <Button
            onClick={() => setQuery("Generate a weekly financial summary")}
            variant="outline"
            className="h-auto p-4 flex flex-col items-center"
          >
            <span className="text-sm font-medium">Financial Report</span>
            <span className="text-xs text-gray-500 mt-1">Weekly summary</span>
          </Button>
        </div>
      </Card>
    </div>
  );
}
