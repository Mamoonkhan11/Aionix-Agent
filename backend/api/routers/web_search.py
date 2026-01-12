"""
Web search API router.

This module provides endpoints for web search functionality using the autonomous
search agent with SerpAPI integration.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.dependencies import get_current_user
from core.exceptions import ExternalAPIException
from models.user import User
from services.web_search.search_agent import WebSearchAgent

router = APIRouter(prefix="/web-search", tags=["web-search"])


# Pydantic models for API
class SearchRequest(BaseModel):
    """Request model for web search."""
    query: str
    max_results: Optional[int] = 10
    search_type: Optional[str] = "general"


class MultiSearchRequest(BaseModel):
    """Request model for multiple searches."""
    queries: List[str]
    max_results: Optional[int] = 10
    search_type: Optional[str] = "general"


class SearchResult(BaseModel):
    """Response model for search results."""
    title: str
    link: str
    snippet: str
    display_link: str
    source: str
    discovered_at: str
    content_hash: str


class SearchSuggestions(BaseModel):
    """Response model for search suggestions."""
    suggestions: List[str]


# API Endpoints
@router.post("/search", response_model=List[SearchResult])
async def search_web(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Perform a web search using the autonomous search agent.

    Searches the web for new information, filters duplicates, and returns
    relevant results while respecting rate limits.
    """
    try:
        agent = WebSearchAgent()

        results = agent.search_and_process(
            query=request.query,
            max_results=request.max_results,
            search_type=request.search_type
        )

        return [SearchResult(**result) for result in results]

    except ExternalAPIException as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search/multiple", response_model=Dict[str, List[SearchResult]])
async def search_multiple_queries(
    request: MultiSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Perform multiple web searches.

    Useful for researching multiple related topics or gathering comprehensive
    information on a subject area.
    """
    try:
        agent = WebSearchAgent()

        results = agent.search_multiple_queries(
            queries=request.queries,
            max_results=request.max_results,
            search_type=request.search_type
        )

        # Convert results to proper format
        formatted_results = {}
        for query, query_results in results.items():
            formatted_results[query] = [SearchResult(**result) for result in query_results]

        return formatted_results

    except ExternalAPIException as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multiple search failed: {str(e)}")


@router.get("/suggestions", response_model=SearchSuggestions)
async def get_search_suggestions(
    query: str = Query(..., min_length=1, max_length=200),
    current_user: User = Depends(get_current_user)
):
    """
    Get search suggestions for a query.

    Provides autocomplete-style suggestions to help users refine their searches.
    """
    try:
        agent = WebSearchAgent()
        suggestions = agent.get_search_suggestions(query)

        return SearchSuggestions(suggestions=suggestions)

    except ExternalAPIException as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/search/{query}", response_model=List[SearchResult])
async def quick_search(
    query: str,
    max_results: int = Query(10, description="Maximum number of results"),
    search_type: str = Query("general", description="Type of search: general, news, academic, images"),
    current_user: User = Depends(get_current_user)
):
    """
    Quick web search endpoint.

    Simplified endpoint for quick searches using URL parameters.
    """
    try:
        agent = WebSearchAgent()

        results = agent.search_and_process(
            query=query,
            max_results=max_results,
            search_type=search_type
        )

        return [SearchResult(**result) for result in results]

    except ExternalAPIException as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick search failed: {str(e)}")


@router.get("/status")
async def get_search_status(current_user: User = Depends(get_current_user)):
    """
    Get the status of the web search service.

    Returns information about rate limits and service health.
    """
    try:
        agent = WebSearchAgent()

        # Basic status check
        status = {
            "service": "web_search_agent",
            "status": "healthy",
            "api_configured": bool(agent.api_key),
            "rate_limits": {
                "requests_per_minute": agent.requests_per_minute,
                "requests_per_day": agent.requests_per_day,
                "daily_used": agent.daily_request_count,
                "daily_remaining": max(0, agent.requests_per_day - agent.daily_request_count)
            },
            "cache_size": len(agent.seen_hashes),
            "max_cache_size": agent.max_cache_size
        }

        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
