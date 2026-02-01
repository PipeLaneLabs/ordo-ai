"""
Cache (Redis)

Redis client for rate limiting, session storage, and distributed locks.
Implements async operations with connection pooling and error handling.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as redis
import structlog

from src.config import settings
from src.exceptions import CacheError


logger = structlog.get_logger(__name__)


class RedisCache:
    """
    Redis client for caching, rate limiting, and distributed locks.

    Provides async interface for common Redis operations with automatic
    connection pooling and error handling.
    """

    def __init__(self) -> None:
        """Initialize Redis client with connection pool."""
        self.redis_url = settings.redis_url
        self.pool: redis.ConnectionPool | None = None
        self.client: redis.Redis | None = None

    async def connect(self) -> None:
        """
        Establish Redis connection pool.

        Raises:
            CacheError: If connection fails
        """
        try:
            self.pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=10,
            )
            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            await self.client.ping()

            logger.info(
                "redis.connected",
                url=self.redis_url,
                max_connections=10,
            )

        except redis.RedisError as e:
            logger.error(
                "redis.connection_failed",
                url=self.redis_url,
                error=str(e),
            )
            raise CacheError(f"Failed to connect to Redis: {e}") from e

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self.client:
            await self.client.aclose()
            logger.info("redis.disconnected")

    async def get(self, key: str) -> str | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> value = await cache.get("user:123:session")
        """
        if not self.client:
            raise CacheError("Redis client not connected")

        try:
            value = await self.client.get(key)
            logger.debug("cache.get", key=key, found=value is not None)
            return value  # type: ignore[no-any-return]

        except redis.RedisError as e:
            logger.error("cache.get_failed", key=key, error=str(e))
            raise CacheError(f"Failed to get cache key: {e}") from e

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: Time-to-live in seconds (None = no expiration)

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> await cache.set("user:123:session", "token", ttl_seconds=3600)
        """
        if not self.client:
            raise CacheError("Redis client not connected")

        try:
            if ttl_seconds:
                await self.client.setex(key, ttl_seconds, value)
            else:
                await self.client.set(key, value)

            logger.debug(
                "cache.set",
                key=key,
                ttl_seconds=ttl_seconds,
            )

        except redis.RedisError as e:
            logger.error("cache.set_failed", key=key, error=str(e))
            raise CacheError(f"Failed to set cache key: {e}") from e

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if key didn't exist

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> deleted = await cache.delete("user:123:session")
        """
        if not self.client:
            raise CacheError("Redis client not connected")

        try:
            result = await self.client.delete(key)
            deleted = result > 0

            logger.debug("cache.delete", key=key, deleted=deleted)
            return deleted  # type: ignore[no-any-return]

        except redis.RedisError as e:
            logger.error("cache.delete_failed", key=key, error=str(e))
            raise CacheError(f"Failed to delete cache key: {e}") from e

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> exists = await cache.exists("user:123:session")
        """
        if not self.client:
            raise CacheError("Redis client not connected")

        try:
            result = await self.client.exists(key)
            exists = result > 0

            logger.debug("cache.exists", key=key, exists=exists)
            return exists  # type: ignore[no-any-return]

        except redis.RedisError as e:
            logger.error("cache.exists_failed", key=key, error=str(e))
            raise CacheError(f"Failed to check cache key: {e}") from e

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter in cache.

        Args:
            key: Cache key
            amount: Amount to increment by (default: 1)

        Returns:
            New value after increment

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> count = await cache.increment("api:requests:user:123")
        """
        if not self.client:
            raise CacheError("Redis client not connected")

        try:
            new_value = await self.client.incrby(key, amount)
            logger.debug("cache.increment", key=key, amount=amount, new_value=new_value)
            return new_value  # type: ignore[no-any-return]

        except redis.RedisError as e:
            logger.error("cache.increment_failed", key=key, error=str(e))
            raise CacheError(f"Failed to increment cache key: {e}") from e

    async def rate_limit(
        self, key: str, max_requests: int, window_seconds: int
    ) -> bool:
        """
        Check rate limit using sliding window.

        Args:
            key: Rate limit key (e.g., "api:user:123")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False if rate limit exceeded

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> allowed = await cache.rate_limit(
            ...     "api:user:123",
            ...     max_requests=50,
            ...     window_seconds=60
            ... )
            >>> if not allowed:
            ...     raise Exception("Rate limit exceeded")
        """
        if not self.client:
            raise CacheError("Redis client not connected")

        try:
            # Increment counter
            current = await self.client.incr(key)

            # Set expiration on first request
            if current == 1:
                await self.client.expire(key, window_seconds)

            allowed = current <= max_requests

            logger.info(
                "rate_limit.checked",
                key=key,
                current=current,
                max_requests=max_requests,
                window_seconds=window_seconds,
                allowed=allowed,
            )

            return allowed  # type: ignore[no-any-return]

        except redis.RedisError as e:
            logger.error("rate_limit.check_failed", key=key, error=str(e))
            raise CacheError(f"Failed to check rate limit: {e}") from e

    @asynccontextmanager
    async def lock(
        self, key: str, timeout_seconds: int = 60
    ) -> AsyncGenerator[bool, None]:
        """
        Acquire distributed lock with automatic release.

        Args:
            key: Lock key
            timeout_seconds: Lock timeout in seconds (default: 60)

        Yields:
            True if lock was acquired, False otherwise

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> async with cache.lock("workflow:wf-001") as acquired:
            ...     if acquired:
            ...         # Critical section
            ...         await process_workflow()
            ...     else:
            ...         print("Could not acquire lock")
        """
        if not self.client:
            raise CacheError("Redis client not connected")

        lock_key = f"lock:{key}"
        acquired = False

        try:
            # Try to acquire lock
            acquired = await self.client.set(lock_key, "1", nx=True, ex=timeout_seconds)

            if acquired:
                logger.info(
                    "lock.acquired",
                    key=key,
                    timeout_seconds=timeout_seconds,
                )
            else:
                logger.warning(
                    "lock.acquisition_failed",
                    key=key,
                    reason="Lock already held",
                )

            yield bool(acquired)

        except redis.RedisError as e:
            logger.error("lock.error", key=key, error=str(e))
            raise CacheError(f"Lock operation failed: {e}") from e

        finally:
            # Release lock if we acquired it
            if acquired:
                try:
                    await self.client.delete(lock_key)
                    logger.info("lock.released", key=key)
                except redis.RedisError as e:
                    logger.error("lock.release_failed", key=key, error=str(e))

    async def set_session(
        self, session_id: str, user_id: str, ttl_hours: int = 24
    ) -> None:
        """
        Store user session with TTL.

        Args:
            session_id: Session identifier
            user_id: User identifier
            ttl_hours: Session expiration in hours (default: 24)

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> await cache.set_session("sess-123", "user-456", ttl_hours=24)
        """
        key = f"session:{session_id}"
        ttl_seconds = ttl_hours * 3600

        await self.set(key, user_id, ttl_seconds=ttl_seconds)

        logger.info(
            "session.created",
            session_id=session_id,
            user_id=user_id,
            ttl_hours=ttl_hours,
        )

    async def get_session(self, session_id: str) -> str | None:
        """
        Retrieve user ID from session.

        Args:
            session_id: Session identifier

        Returns:
            User ID if session exists, None otherwise

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> user_id = await cache.get_session("sess-123")
        """
        key = f"session:{session_id}"
        user_id = await self.get(key)

        logger.debug(
            "session.retrieved",
            session_id=session_id,
            found=user_id is not None,
        )

        return user_id

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete user session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if didn't exist

        Raises:
            CacheError: If operation fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()
            >>> deleted = await cache.delete_session("sess-123")
        """
        key = f"session:{session_id}"
        deleted = await self.delete(key)

        logger.info(
            "session.deleted",
            session_id=session_id,
            deleted=deleted,
        )

        return deleted


# Global cache instance
cache = RedisCache()
