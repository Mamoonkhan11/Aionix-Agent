'use client';

import { useEffect, useState } from 'react';
import AgentInteraction from '../../../components/Agents/AgentInteraction';

export default function AgentsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI Agent Interaction</h1>
        <p className="text-gray-600 mt-2">
          Interact with specialized AI agents for finance, research, news analysis, and more.
        </p>
      </div>

      <AgentInteraction />
    </div>
  );
}
