"""
AI Agents API router.

This module provides endpoints for interacting with the pluggable AI agent framework,
including agent discovery, execution, and management.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.dependencies import get_current_user
from ai_engine.agents.agent_registry import get_agent_registry
from ai_engine.agents.base_agent import AgentConfig, AgentContext
from models.user import User

router = APIRouter(prefix="/agents", tags=["agents"])


# Pydantic models for API
class AgentInfo(BaseModel):
    """Agent information response model."""
    name: str
    class_name: str
    description: str
    capabilities: List[str]
    module: str


class AgentDetail(BaseModel):
    """Detailed agent information."""
    name: str
    class_name: str
    module: str
    description: str
    capabilities: List[str]
    config_schema: Dict
    methods: List[str]


class AgentExecutionRequest(BaseModel):
    """Request model for agent execution."""
    query: str
    agent_config: Optional[Dict] = None
    context_metadata: Optional[Dict] = None


class AgentExecutionResponse(BaseModel):
    """Response model for agent execution."""
    success: bool
    response: str
    data: Dict
    actions_taken: List[str]
    confidence_score: float
    reasoning_steps: List[str]
    execution_time: float
    timestamp: str


class AgentChainRequest(BaseModel):
    """Request model for agent chaining."""
    agent_names: List[str]
    query: str
    agent_config: Optional[Dict] = None


# API Endpoints
@router.get("/", response_model=List[AgentInfo])
async def list_agents(
    capability: Optional[str] = Query(None, description="Filter by capability"),
    current_user: User = Depends(get_current_user)
):
    """
    List all available AI agents.

    Optionally filter by capability to find agents with specific skills.
    """
    try:
        registry = get_agent_registry()

        if capability:
            # Filter by capability
            agent_names = registry.get_agents_by_capability(capability)
            all_agents = registry.list_agents()
            agents = [agent for agent in all_agents if agent["name"] in agent_names]
        else:
            agents = registry.list_agents()

        return [
            AgentInfo(
                name=agent["name"],
                class_name=agent["class"],
                description=agent["description"],
                capabilities=agent["capabilities"],
                module=agent["module"]
            )
            for agent in agents
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get("/{agent_name}", response_model=AgentDetail)
async def get_agent_details(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific agent.
    """
    try:
        registry = get_agent_registry()
        agent_info = registry.get_agent_info(agent_name)

        return AgentDetail(**agent_info)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent details: {str(e)}")


@router.post("/{agent_name}/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    agent_name: str,
    request: AgentExecutionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Execute a specific AI agent with the given query.
    """
    try:
        registry = get_agent_registry()

        # Create agent config if provided
        agent_config = None
        if request.agent_config:
            agent_config = AgentConfig(**request.agent_config)

        # Create execution context
        context = AgentContext(
            user_id=str(current_user.id),
            session_id=None,  # Could be enhanced to support sessions
            metadata=request.context_metadata or {}
        )

        # Execute the agent
        result = await registry.execute_agent(
            name=agent_name,
            query=request.query,
            context=context,
            config=agent_config
        )

        return AgentExecutionResponse(
            success=result.success,
            response=result.response,
            data=result.data,
            actions_taken=result.actions_taken,
            confidence_score=result.confidence_score,
            reasoning_steps=result.reasoning_steps,
            execution_time=result.execution_time,
            timestamp=result.timestamp.isoformat()
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@router.post("/chain/execute", response_model=AgentExecutionResponse)
async def execute_agent_chain(
    request: AgentChainRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Execute a chain of agents sequentially.

    Agents will process the query in order, with each agent receiving
    the output of the previous agent.
    """
    try:
        registry = get_agent_registry()

        # Create the agent chain
        first_agent = registry.create_agent_chain(request.agent_names)

        if not first_agent:
            raise HTTPException(status_code=400, detail="Failed to create agent chain")

        # Create agent config if provided
        agent_config = None
        if request.agent_config:
            agent_config = AgentConfig(**request.agent_config)

        # Create execution context
        context = AgentContext(
            user_id=str(current_user.id),
            session_id=None,
            metadata={"chain_execution": True, "chain_agents": request.agent_names}
        )

        # Execute the chain
        result = await first_agent.execute_chain(request.query, context)

        return AgentExecutionResponse(
            success=result.success,
            response=result.response,
            data=result.data,
            actions_taken=result.actions_taken,
            confidence_score=result.confidence_score,
            reasoning_steps=result.reasoning_steps,
            execution_time=result.execution_time,
            timestamp=result.timestamp.isoformat()
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent chain execution failed: {str(e)}")


@router.get("/capabilities/{capability}")
async def get_agents_by_capability(
    capability: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all agents that have a specific capability.
    """
    try:
        registry = get_agent_registry()
        agent_names = registry.get_agents_by_capability(capability)

        if not agent_names:
            return {"capability": capability, "agents": []}

        # Get detailed info for each agent
        agents = []
        for name in agent_names:
            try:
                agent_info = registry.get_agent_info(name)
                agents.append({
                    "name": name,
                    "description": agent_info.get("description", ""),
                    "capabilities": agent_info.get("capabilities", [])
                })
            except Exception:
                continue

        return {
            "capability": capability,
            "agents": agents,
            "count": len(agents)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agents by capability: {str(e)}")


@router.post("/{agent_name}/validate-config")
async def validate_agent_config(
    agent_name: str,
    config: Dict,
    current_user: User = Depends(get_current_user)
):
    """
    Validate agent configuration.
    """
    try:
        registry = get_agent_registry()

        is_valid = registry.validate_agent_config(agent_name, config)

        return {
            "agent_name": agent_name,
            "config_valid": is_valid,
            "config": config
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Config validation failed: {str(e)}")


@router.get("/registry/stats")
async def get_registry_stats(current_user: User = Depends(get_current_user)):
    """
    Get agent registry statistics.
    """
    try:
        registry = get_agent_registry()
        stats = registry.get_stats()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get registry stats: {str(e)}")


@router.post("/discover/{module_path}")
async def discover_agents_in_module(
    module_path: str,
    current_user: User = Depends(get_current_user)
):
    """
    Discover and register agents in a Python module.

    This endpoint allows dynamic loading of agent classes from external modules.
    """
    try:
        registry = get_agent_registry()
        discovered_agents = registry.discover_agents_in_module(module_path)

        return {
            "module_path": module_path,
            "discovered_agents": discovered_agents,
            "count": len(discovered_agents)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent discovery failed: {str(e)}")


@router.delete("/cache/clear")
async def clear_agent_cache(current_user: User = Depends(get_current_user)):
    """
    Clear cached agent instances.

    This forces recreation of agent instances on next use.
    """
    try:
        registry = get_agent_registry()
        registry.clear_cache()

        return {"message": "Agent cache cleared successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")
