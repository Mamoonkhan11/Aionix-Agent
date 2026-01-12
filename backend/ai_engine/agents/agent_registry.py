"""
Agent registry and management system.

This module provides the central registry for managing AI agents, including
dynamic registration, discovery, and execution of specialized agents.
"""

import importlib
import inspect
import logging
from typing import Any, Dict, List, Optional, Type

from ai_engine.agents.base_agent import BaseAgent, AgentConfig, AgentContext, AgentResult

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for AI agents.

    Provides agent discovery, registration, instantiation, and management
    capabilities for the pluggable agent framework.
    """

    def __init__(self):
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._agent_instances: Dict[str, BaseAgent] = {}
        self._agent_metadata: Dict[str, Dict[str, Any]] = {}

        # Register built-in agents
        self._register_builtin_agents()

    def register_agent(self, agent_class: Type[BaseAgent], name: Optional[str] = None) -> None:
        """
        Register an agent class.

        Args:
            agent_class: The agent class to register
            name: Optional custom name for the agent (defaults to class name)
        """
        agent_name = name or agent_class.__name__

        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"Agent class {agent_class} must inherit from BaseAgent")

        self._agents[agent_name] = agent_class
        self._agent_metadata[agent_name] = agent_class.get_agent_info()

        logger.info(f"Registered agent: {agent_name}")

    def unregister_agent(self, name: str) -> None:
        """
        Unregister an agent.

        Args:
            name: Name of the agent to unregister
        """
        if name in self._agents:
            del self._agents[name]
            if name in self._agent_metadata:
                del self._agent_metadata[name]
            if name in self._agent_instances:
                del self._agent_instances[name]
            logger.info(f"Unregistered agent: {name}")
        else:
            logger.warning(f"Agent {name} not found for unregistration")

    def get_agent(self, name: str, config: Optional[AgentConfig] = None) -> BaseAgent:
        """
        Get an agent instance.

        Args:
            name: Name of the agent
            config: Optional configuration for the agent

        Returns:
            Agent instance
        """
        if name not in self._agents:
            raise ValueError(f"Agent {name} not registered")

        # Return cached instance if it exists and config matches
        if name in self._agent_instances:
            instance = self._agent_instances[name]
            if config is None or instance.config == config:
                return instance

        # Create new instance
        agent_class = self._agents[name]
        if config is None:
            # Use default config from agent metadata
            default_config = self._agent_metadata[name].get("config_schema", {})
            config = AgentConfig(**default_config)

        instance = agent_class(config)
        self._agent_instances[name] = instance

        return instance

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all registered agents with their metadata.

        Returns:
            List of agent information dictionaries
        """
        return [
            {
                "name": name,
                "class": agent_class.__name__,
                "description": metadata.get("description", ""),
                "capabilities": metadata.get("capabilities", []),
                "module": agent_class.__module__
            }
            for name, agent_class in self._agents.items()
            for metadata in [self._agent_metadata.get(name, {})]
        ]

    def get_agent_info(self, name: str) -> Dict[str, Any]:
        """
        Get detailed information about an agent.

        Args:
            name: Name of the agent

        Returns:
            Agent metadata and information
        """
        if name not in self._agents:
            raise ValueError(f"Agent {name} not registered")

        metadata = self._agent_metadata.get(name, {})
        agent_class = self._agents[name]

        return {
            "name": name,
            "class": agent_class.__name__,
            "module": agent_class.__module__,
            "description": metadata.get("description", ""),
            "capabilities": metadata.get("capabilities", []),
            "config_schema": metadata.get("config_schema", {}),
            "methods": self._get_agent_methods(agent_class)
        }

    async def execute_agent(
        self,
        name: str,
        query: str,
        context: AgentContext,
        config: Optional[AgentConfig] = None
    ) -> AgentResult:
        """
        Execute an agent with the given query and context.

        Args:
            name: Name of the agent to execute
            query: The query or task for the agent
            context: Execution context
            config: Optional agent configuration

        Returns:
            Agent execution result
        """
        agent = self.get_agent(name, config)

        logger.info(f"Executing agent {name} with query: {query[:100]}...")

        result = await agent.execute(query, context)

        logger.info(f"Agent {name} execution completed with success: {result.success}")

        return result

    def discover_agents_in_module(self, module_path: str) -> List[str]:
        """
        Discover and register agents in a Python module.

        Args:
            module_path: Python module path (e.g., 'myapp.agents')

        Returns:
            List of discovered agent names
        """
        try:
            module = importlib.import_module(module_path)
            discovered_agents = []

            # Find all classes in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseAgent) and
                    obj != BaseAgent):

                    self.register_agent(obj, name)
                    discovered_agents.append(name)

            logger.info(f"Discovered {len(discovered_agents)} agents in module {module_path}")
            return discovered_agents

        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {str(e)}")
            return []

    def create_agent_chain(self, agent_names: List[str]) -> Optional[BaseAgent]:
        """
        Create a chain of agents for sequential execution.

        Args:
            agent_names: List of agent names in execution order

        Returns:
            First agent in the chain, or None if chain creation fails
        """
        if not agent_names:
            return None

        # Get the first agent
        first_agent = self.get_agent(agent_names[0])

        # Chain subsequent agents
        current_agent = first_agent
        for agent_name in agent_names[1:]:
            next_agent = self.get_agent(agent_name)
            if hasattr(current_agent, 'chain'):
                current_agent.chain(next_agent)
                current_agent = next_agent
            else:
                logger.warning(f"Agent {agent_names[0]} does not support chaining")
                return first_agent

        return first_agent

    def get_agents_by_capability(self, capability: str) -> List[str]:
        """
        Find agents that have a specific capability.

        Args:
            capability: The capability to search for

        Returns:
            List of agent names that have the capability
        """
        matching_agents = []

        for name, metadata in self._agent_metadata.items():
            capabilities = metadata.get("capabilities", [])
            if capability in capabilities:
                matching_agents.append(name)

        return matching_agents

    def validate_agent_config(self, name: str, config: Dict[str, Any]) -> bool:
        """
        Validate agent configuration.

        Args:
            name: Agent name
            config: Configuration dictionary

        Returns:
            True if configuration is valid
        """
        if name not in self._agents:
            return False

        try:
            AgentConfig(**config)
            return True
        except Exception:
            return False

    def _register_builtin_agents(self) -> None:
        """Register built-in agents."""
        try:
            # Import and register built-in agents
            from ai_engine.agents.finance_agent import FinanceAgent
            from ai_engine.agents.news_agent import NewsAgent
            from ai_engine.agents.research_agent import ResearchAgent

            self.register_agent(FinanceAgent, "finance_agent")
            self.register_agent(NewsAgent, "news_agent")
            self.register_agent(ResearchAgent, "research_agent")

            logger.info("Registered built-in agents")

        except ImportError as e:
            logger.warning(f"Failed to import built-in agents: {str(e)}")

    def _get_agent_methods(self, agent_class: Type[BaseAgent]) -> List[str]:
        """Get list of public methods for an agent class."""
        methods = []

        for name, method in inspect.getmembers(agent_class, predicate=inspect.isfunction):
            if not name.startswith('_'):
                methods.append(name)

        return methods

    def clear_cache(self) -> None:
        """Clear cached agent instances."""
        self._agent_instances.clear()
        logger.info("Cleared agent instance cache")

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_agents": len(self._agents),
            "cached_instances": len(self._agent_instances),
            "agents_by_capability": self._count_capabilities()
        }

    def _count_capabilities(self) -> Dict[str, int]:
        """Count agents by capability."""
        capability_counts = {}

        for metadata in self._agent_metadata.values():
            capabilities = metadata.get("capabilities", [])
            for capability in capabilities:
                capability_counts[capability] = capability_counts.get(capability, 0) + 1

        return capability_counts


# Global agent registry instance
agent_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    return agent_registry


# Utility functions for agent management
async def execute_agent_by_capability(
    capability: str,
    query: str,
    context: AgentContext,
    config: Optional[AgentConfig] = None
) -> Optional[AgentResult]:
    """
    Execute the first available agent with the specified capability.

    Args:
        capability: Required capability
        query: Query to execute
        context: Execution context
        config: Optional agent configuration

    Returns:
        Agent result or None if no suitable agent found
    """
    registry = get_agent_registry()
    agent_names = registry.get_agents_by_capability(capability)

    if not agent_names:
        logger.warning(f"No agents found with capability: {capability}")
        return None

    # Use the first available agent
    agent_name = agent_names[0]
    return await registry.execute_agent(agent_name, query, context, config)


def create_agent_from_config(config: Dict[str, Any]) -> Optional[BaseAgent]:
    """
    Create an agent instance from configuration dictionary.

    Args:
        config: Agent configuration dictionary

    Returns:
        Agent instance or None if creation fails
    """
    registry = get_agent_registry()

    try:
        agent_name = config.get("name")
        agent_config = config.get("config", {})

        if not agent_name:
            logger.error("Agent name not specified in config")
            return None

        agent_config_obj = AgentConfig(**agent_config)
        return registry.get_agent(agent_name, agent_config_obj)

    except Exception as e:
        logger.error(f"Failed to create agent from config: {str(e)}")
        return None
