"""
Autonomous web search agent using SerpAPI.

This module provides an agent that can autonomously search the web for new information,
deduplicate results, and feed them into the AI pipeline while respecting rate limits.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import requests
from serpapi import GoogleSearch

from core.config.settings import settings
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)


class SearchResult:
    """Represents a web search result."""

    def __init__(
        self,
        title: str,
        link: str,
        snippet: str,
        display_link: Optional[str] = None,
        source: str = "unknown"
    ):
        self.title = title
        self.link = link
        self.snippet = snippet
        self.display_link = display_link or self._extract_domain(link)
        self.source = source
        self.discovered_at = datetime.now()
        self.content_hash = self._generate_content_hash()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except Exception:
            return url

    def _generate_content_hash(self) -> str:
        """Generate a hash of the content for deduplication."""
        content = f"{self.title}{self.link}{self.snippet}".lower()
        return hashlib.md5(content.encode()).hexdigest()

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "title": self.title,
            "link": self.link,
            "snippet": self.snippet,
            "display_link": self.display_link,
            "source": self.source,
            "discovered_at": self.discovered_at.isoformat(),
            "content_hash": self.content_hash
        }


class WebSearchAgent:
    """
    Autonomous web search agent using SerpAPI.

    Features:
    - Searches the web for new information
    - Avoids duplicate data using content hashing
    - Respects rate limits and handles errors gracefully
    - Feeds new content into AI pipeline
    """

    def __init__(self):
        self.api_key = settings.SERPAPI_API_KEY
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY is required for web search functionality")

        # Rate limiting
        self.requests_per_minute = 10  # SerpAPI limit
        self.requests_per_day = 100  # Conservative daily limit
        self.last_request_time = None
        self.daily_request_count = 0
        self.day_start = datetime.now().date()

        # Deduplication
        self.seen_hashes: Set[str] = set()
        self.max_cache_size = 10000

        # Content filtering
        self.min_snippet_length = 50
        self.blacklisted_domains = {
            "facebook.com", "twitter.com", "instagram.com",
            "youtube.com", "linkedin.com", "pinterest.com"
        }

    def search_and_process(
        self,
        query: str,
        max_results: int = 10,
        search_type: str = "general",
        **kwargs
    ) -> List[Dict]:
        """
        Search the web and process results.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            search_type: Type of search (general, news, academic, etc.)
            **kwargs: Additional search parameters

        Returns:
            List of processed search results
        """
        try:
            # Check rate limits
            self._check_rate_limits()

            # Perform search
            raw_results = self._perform_search(query, max_results, search_type, **kwargs)

            # Process and filter results
            processed_results = self._process_results(raw_results)

            # Filter duplicates
            new_results = self._filter_duplicates(processed_results)

            logger.info(f"Web search completed: {len(new_results)} new results from {len(processed_results)} total")

            return new_results

        except Exception as e:
            logger.error(f"Error in web search: {str(e)}")
            raise ExternalAPIException(f"Web search failed: {str(e)}")

    def _perform_search(
        self,
        query: str,
        max_results: int,
        search_type: str,
        **kwargs
    ) -> List[Dict]:
        """
        Perform the actual search using SerpAPI.

        Args:
            query: Search query
            max_results: Maximum results to fetch
            search_type: Type of search
            **kwargs: Additional parameters

        Returns:
            Raw search results from SerpAPI
        """
        # Prepare search parameters
        params = {
            "q": query,
            "api_key": self.api_key,
            "num": min(max_results, 10),  # SerpAPI limit
            "engine": "google"
        }

        # Customize based on search type
        if search_type == "news":
            params["tbm"] = "nws"
            params["engine"] = "google_news"
        elif search_type == "academic":
            params["engine"] = "google_scholar"
        elif search_type == "images":
            params["tbm"] = "isch"
            params["engine"] = "google_images"

        # Add additional parameters
        params.update(kwargs)

        # Perform search
        search = GoogleSearch(params)
        results = search.get_dict()

        # Update rate limiting
        self._update_rate_limits()

        return self._extract_search_results(results, search_type)

    def _extract_search_results(self, serpapi_response: Dict, search_type: str) -> List[Dict]:
        """Extract search results from SerpAPI response."""
        results = []

        try:
            if search_type == "news":
                # Extract from news results
                news_results = serpapi_response.get("news_results", [])
                for item in news_results:
                    result = {
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "display_link": item.get("displayed_link", ""),
                        "source": item.get("source", {}).get("name", "unknown") if isinstance(item.get("source"), dict) else "unknown",
                        "published": item.get("date", "")
                    }
                    results.append(result)

            elif search_type == "images":
                # Extract from image results
                image_results = serpapi_response.get("images_results", [])
                for item in image_results[:10]:  # Limit image results
                    result = {
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "display_link": item.get("displayed_link", ""),
                        "source": "image_search"
                    }
                    results.append(result)

            else:
                # Extract from general search results
                organic_results = serpapi_response.get("organic_results", [])
                for item in organic_results:
                    result = {
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "display_link": item.get("displayed_link", ""),
                        "source": "web_search"
                    }
                    results.append(result)

        except Exception as e:
            logger.error(f"Error extracting search results: {str(e)}")

        return results

    def _process_results(self, raw_results: List[Dict]) -> List[SearchResult]:
        """Process raw search results into SearchResult objects."""
        processed = []

        for result in raw_results:
            try:
                # Skip if missing essential fields
                if not result.get("title") or not result.get("link"):
                    continue

                # Skip blacklisted domains
                domain = urlparse(result["link"]).netloc
                if any(blacklisted in domain for blacklisted in self.blacklisted_domains):
                    continue

                # Skip short snippets
                snippet = result.get("snippet", "")
                if len(snippet) < self.min_snippet_length:
                    continue

                # Create SearchResult object
                search_result = SearchResult(
                    title=result["title"],
                    link=result["link"],
                    snippet=snippet,
                    display_link=result.get("display_link"),
                    source=result.get("source", "web_search")
                )

                processed.append(search_result)

            except Exception as e:
                logger.warning(f"Error processing search result: {str(e)}")
                continue

        return processed

    def _filter_duplicates(self, results: List[SearchResult]) -> List[Dict]:
        """Filter out duplicate results based on content hash."""
        new_results = []

        for result in results:
            if result.content_hash not in self.seen_hashes:
                self.seen_hashes.add(result.content_hash)
                new_results.append(result.to_dict())

                # Limit cache size
                if len(self.seen_hashes) > self.max_cache_size:
                    # Remove oldest half of hashes (simple LRU approximation)
                    sorted_hashes = sorted(self.seen_hashes)
                    self.seen_hashes = set(sorted_hashes[len(sorted_hashes)//2:])

        return new_results

    def _check_rate_limits(self):
        """Check and enforce rate limits."""
        now = datetime.now()

        # Reset daily counter if new day
        if now.date() != self.day_start:
            self.daily_request_count = 0
            self.day_start = now.date()

        # Check daily limit
        if self.daily_request_count >= self.requests_per_day:
            raise ExternalAPIException("Daily API request limit exceeded")

        # Check per-minute limit
        if self.last_request_time:
            time_diff = (now - self.last_request_time).total_seconds()
            if time_diff < 60 and self.requests_per_minute <= 0:
                wait_time = 60 - time_diff
                logger.info(f"Rate limited, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)

    def _update_rate_limits(self):
        """Update rate limiting counters."""
        self.last_request_time = datetime.now()
        self.daily_request_count += 1

    def get_search_suggestions(self, query: str) -> List[str]:
        """Get search suggestions for a query."""
        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google_autocomplete"
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            suggestions = []
            for suggestion in results.get("suggestions", []):
                if isinstance(suggestion, dict) and "value" in suggestion:
                    suggestions.append(suggestion["value"])

            return suggestions[:5]  # Limit to 5 suggestions

        except Exception as e:
            logger.error(f"Error getting search suggestions: {str(e)}")
            return []

    def search_multiple_queries(self, queries: List[str], **kwargs) -> Dict[str, List[Dict]]:
        """
        Search multiple queries and return combined results.

        Args:
            queries: List of search queries
            **kwargs: Additional search parameters

        Returns:
            Dictionary mapping queries to their results
        """
        results = {}

        for query in queries:
            try:
                query_results = self.search_and_process(query, **kwargs)
                results[query] = query_results

                # Small delay between queries to respect rate limits
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error searching query '{query}': {str(e)}")
                results[query] = []

        return results
