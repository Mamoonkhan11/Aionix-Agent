"""
Rate limiting utilities.

This module provides rate limiting functionality to prevent API quota exhaustion
and ensure compliance with external service rate limits.
"""

import asyncio
import time
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter for API requests.

    Implements a token bucket algorithm to limit the rate of requests
    while allowing burst capacity.
    """

    def __init__(self, requests_per_hour: int, burst_capacity: Optional[int] = None):
        """
        Initialize rate limiter.

        Args:
            requests_per_hour: Maximum requests per hour
            burst_capacity: Maximum burst capacity (defaults to requests_per_hour)
        """
        self.requests_per_hour = requests_per_hour
        self.burst_capacity = burst_capacity or requests_per_hour

        # Convert to requests per second for internal calculations
        self.requests_per_second = requests_per_hour / 3600.0

        # Token bucket state
        self.tokens = self.burst_capacity
        self.last_update = time.time()

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def wait_if_needed(self) -> None:
        """
        Wait if necessary to comply with rate limit.

        This method will block until enough tokens are available
        to make a request.
        """
        async with self._lock:
            current_time = time.time()
            time_passed = current_time - self.last_update

            # Add tokens based on time passed
            self.tokens = min(
                self.burst_capacity,
                self.tokens + time_passed * self.requests_per_second
            )

            if self.tokens < 1.0:
                # Calculate wait time
                wait_time = (1.0 - self.tokens) / self.requests_per_second
                await asyncio.sleep(wait_time)

                # Recalculate after waiting
                current_time = time.time()
                time_passed = current_time - self.last_update
                self.tokens = min(
                    self.burst_capacity,
                    self.tokens + time_passed * self.requests_per_second
                )

            # Consume a token
            self.tokens -= 1.0
            self.last_update = current_time

    def can_make_request(self) -> bool:
        """
        Check if a request can be made without waiting.

        Returns:
            bool: True if request can be made immediately
        """
        current_time = time.time()
        time_passed = current_time - self.last_update

        available_tokens = min(
            self.burst_capacity,
            self.tokens + time_passed * self.requests_per_second
        )

        return available_tokens >= 1.0

    def time_until_next_request(self) -> float:
        """
        Get time in seconds until next request can be made.

        Returns:
            float: Seconds to wait before next request
        """
        if self.can_make_request():
            return 0.0

        current_time = time.time()
        time_passed = current_time - self.last_update

        available_tokens = min(
            self.burst_capacity,
            self.tokens + time_passed * self.requests_per_second
        )

        return (1.0 - available_tokens) / self.requests_per_second


class FixedWindowRateLimiter:
    """
    Fixed window rate limiter.

    Limits requests within fixed time windows (e.g., per minute, per hour).
    """

    def __init__(self, requests_per_window: int, window_seconds: int):
        """
        Initialize fixed window rate limiter.

        Args:
            requests_per_window: Maximum requests per time window
            window_seconds: Window duration in seconds
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds

        self.current_window_start = time.time()
        self.request_count = 0

        self._lock = asyncio.Lock()

    async def wait_if_needed(self) -> None:
        """
        Wait if necessary to comply with rate limit.
        """
        async with self._lock:
            current_time = time.time()

            # Check if we're in a new window
            if current_time - self.current_window_start >= self.window_seconds:
                self.current_window_start = current_time
                self.request_count = 0

            if self.request_count >= self.requests_per_window:
                # Wait until next window
                wait_time = self.window_seconds - (current_time - self.current_window_start)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

                # Reset for new window
                self.current_window_start = time.time()
                self.request_count = 0

            self.request_count += 1
