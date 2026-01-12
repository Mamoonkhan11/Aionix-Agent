"""
Base agent framework for pluggable AI agents.

This module defines the base classes and interfaces for creating specialized
AI agents that can be dynamically registered and executed within the system.
"""

import abc
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ai_engine.llm_client import LLMClient
from ai_engine.memory.memory_service import MemoryService
from core.config.settings import settings

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Configuration for an AI agent."""
    name: str = Field(..., description="Agent name")
    description: str = Field("", description="Agent description")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific parameters")
    memory_enabled: bool = Field(True, description="Whether to use memory")
    max_iterations: int = Field(10, description="Maximum reasoning iterations")
    temperature: float = Field(0.7, description="LLM temperature")
    model: Optional[str] = Field(None, description="Specific model to use")


class AgentContext(BaseModel):
    """Context information passed to agents."""
    user_id: str
    session_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentResult(BaseModel):
    """Result returned by an agent."""
    success: bool
    response: str
    data: Dict[str, Any] = Field(default_factory=dict)
    actions_taken: List[str] = Field(default_factory=list)
    confidence_score: float = Field(0.0, min=0.0, max=1.0)
    reasoning_steps: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: float = Field(0.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class BaseAgent(abc.ABC):
    """
    Base class for all AI agents in the system.

    Provides common functionality and defines the interface that all agents must implement.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm_client = LLMClient()
        self.memory_service = MemoryService() if config.memory_enabled else None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def name(self) -> str:
        """Get agent name."""
        return self.config.name

    @property
    def description(self) -> str:
        """Get agent description."""
        return self.config.description

    @property
    def capabilities(self) -> List[str]:
        """Get agent capabilities."""
        return self.config.capabilities

    @abc.abstractmethod
    async def execute(self, query: str, context: AgentContext) -> AgentResult:
        """
        Execute the agent's primary function.

        Args:
            query: The user's query or task
            context: Execution context including user info and history

        Returns:
            AgentResult containing the response and metadata
        """
        pass

    @abc.abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.

        Returns:
            System prompt string
        """
        pass

    async def think(self, query: str, context: AgentContext) -> str:
        """
        Perform reasoning/thinking step.

        Args:
            query: Current query or task
            context: Execution context

        Returns:
            Reasoning result
        """
        system_prompt = self.get_system_prompt()
        user_prompt = self._build_user_prompt(query, context)

        # Add memory context if enabled
        if self.memory_service:
            memory_context = await self._get_memory_context(query, context)
            user_prompt = f"{memory_context}\n\n{user_prompt}"

        response = await self.llm_client.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.config.temperature,
            model=self.config.model,
            max_tokens=2000
        )

        return response

    async def _get_memory_context(self, query: str, context: AgentContext) -> str:
        """Get relevant memory context for the query."""
        if not self.memory_service:
            return ""

        try:
            # Search for relevant memories
            memories = await self.memory_service.search_memories(
                user_id=context.user_id,
                query=query,
                limit=5
            )

            if memories:
                memory_text = "\n".join([m.content for m in memories])
                return f"Relevant context from previous interactions:\n{memory_text}\n"
            else:
                return ""

        except Exception as e:
            self.logger.warning(f"Error retrieving memory context: {str(e)}")
            return ""

    def _build_user_prompt(self, query: str, context: AgentContext) -> str:
        """Build the user prompt with context."""
        prompt_parts = [f"Query: {query}"]

        if context.conversation_history:
            # Include recent conversation history
            recent_history = context.conversation_history[-5:]  # Last 5 messages
            history_text = "\n".join([
                f"{'User' if msg.get('role') == 'user' else 'Assistant'}: {msg.get('content', '')}"
                for msg in recent_history
            ])
            prompt_parts.append(f"Recent conversation:\n{history_text}")

        return "\n\n".join(prompt_parts)

    async def store_memory(self, content: str, context: AgentContext, metadata: Optional[Dict] = None):
        """Store information in memory."""
        if self.memory_service:
            try:
                await self.memory_service.store_memory(
                    user_id=context.user_id,
                    content=content,
                    metadata=metadata or {},
                    agent_name=self.name
                )
            except Exception as e:
                self.logger.warning(f"Error storing memory: {str(e)}")

    def validate_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities

    def get_config_schema(self) -> Dict[str, Any]:
        """Get JSON schema for agent configuration."""
        return self.config.model_json_schema()

    @classmethod
    def get_agent_info(cls) -> Dict[str, Any]:
        """Get static information about the agent class."""
        return {
            "name": cls.__name__,
            "description": cls.__doc__ or "",
            "capabilities": getattr(cls, "DEFAULT_CAPABILITIES", []),
            "config_schema": AgentConfig.model_json_schema()
        }


class ToolCallingAgent(BaseAgent):
    """
    Base class for agents that can call external tools/APIs.

    Extends BaseAgent with tool calling capabilities.
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.available_tools = self._get_available_tools()

    @abc.abstractmethod
    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Define available tools for this agent.

        Returns:
            List of tool definitions in OpenAI tool format
        """
        pass

    @abc.abstractmethod
    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        Execute a specific tool.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool

        Returns:
            Tool execution result
        """
        pass

    async def think_with_tools(self, query: str, context: AgentContext) -> tuple[str, List[Dict]]:
        """
        Perform reasoning with tool calling capability.

        Returns:
            Tuple of (response, tool_calls_made)
        """
        system_prompt = self.get_system_prompt()
        user_prompt = self._build_user_prompt(query, context)

        tool_calls = []
        response = await self.llm_client.generate_response_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=self.available_tools,
            temperature=self.config.temperature,
            model=self.config.model
        )

        # Process tool calls if any
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                try:
                    result = await self.execute_tool(
                        tool_call.function.name,
                        tool_call.function.arguments
                    )
                    tool_calls.append({
                        "tool": tool_call.function.name,
                        "args": tool_call.function.arguments,
                        "result": result
                    })
                except Exception as e:
                    self.logger.error(f"Tool execution failed: {str(e)}")
                    tool_calls.append({
                        "tool": tool_call.function.name,
                        "args": tool_call.function.arguments,
                        "error": str(e)
                    })

        return response.content, tool_calls


class ChainableAgent(BaseAgent):
    """
    Base class for agents that can be chained together.

    Supports pipelining agent outputs to other agents.
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.next_agent: Optional[BaseAgent] = None

    def chain(self, next_agent: BaseAgent) -> BaseAgent:
        """Chain this agent to another agent."""
        self.next_agent = next_agent
        return next_agent

    async def execute_chain(self, query: str, context: AgentContext) -> AgentResult:
        """Execute this agent and any chained agents."""
        # Execute this agent
        result = await self.execute(query, context)

        # If successful and there's a next agent, pass result
        if result.success and self.next_agent:
            # Build new query from this agent's result
            next_query = self._prepare_next_query(result, query)
            next_context = self._prepare_next_context(context, result)

            # Execute next agent in chain
            next_result = await self.next_agent.execute_chain(next_query, next_context)

            # Combine results
            return self._combine_results(result, next_result)

        return result

    def _prepare_next_query(self, current_result: AgentResult, original_query: str) -> str:
        """Prepare query for the next agent in the chain."""
        return f"Based on: {current_result.response}\n\nProcess: {original_query}"

    def _prepare_next_context(self, context: AgentContext, result: AgentResult) -> AgentContext:
        """Prepare context for the next agent."""
        new_history = context.conversation_history + [{
            "role": "assistant",
            "content": result.response,
            "agent": self.name,
            "timestamp": result.timestamp.isoformat()
        }]

        return AgentContext(
            user_id=context.user_id,
            session_id=context.session_id,
            conversation_history=new_history,
            metadata={**context.metadata, "previous_agent": self.name}
        )

    def _combine_results(self, current: AgentResult, next_result: AgentResult) -> AgentResult:
        """Combine results from chained agents."""
        return AgentResult(
            success=next_result.success,
            response=next_result.response,
            data={**current.data, **next_result.data},
            actions_taken=current.actions_taken + next_result.actions_taken,
            confidence_score=min(current.confidence_score, next_result.confidence_score),
            reasoning_steps=current.reasoning_steps + next_result.reasoning_steps,
            metadata={**current.metadata, **next_result.metadata},
            execution_time=current.execution_time + next_result.execution_time
        )
