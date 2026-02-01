"""Unit tests for RedisCache (Redis client)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import CacheError
from src.storage.cache import RedisCache


@pytest.fixture
async def cache():
    """Create RedisCache instance with mocked Redis client."""
    cache = RedisCache()
    cache.client = AsyncMock()
    cache.pool = MagicMock()
    return cache


class TestRedisCacheConnect:
    """Test Redis connection."""

    @pytest.mark.anyio
    async def test_connect_success(self):
        """Test successful Redis connection."""
        mock_pool = MagicMock()
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()

        with patch(
            "src.storage.cache.redis.ConnectionPool.from_url", return_value=mock_pool
        ):
            with patch("src.storage.cache.redis.Redis", return_value=mock_client):
                cache = RedisCache()
                await cache.connect()

                assert cache.pool is not None
                assert cache.client is not None
                mock_client.ping.assert_called_once()

    @pytest.mark.anyio
    async def test_connect_failure(self):
        """Test Redis connection failure."""
        import redis.asyncio as redis

        with patch(
            "src.storage.cache.redis.ConnectionPool.from_url",
            side_effect=redis.RedisError("Connection failed"),
        ):
            cache = RedisCache()
            with pytest.raises(CacheError):
                await cache.connect()


class TestRedisCacheDisconnect:
    """Test Redis disconnection."""

    @pytest.mark.anyio
    async def test_disconnect_success(self, cache):
        """Test successful Redis disconnection."""
        await cache.disconnect()

        cache.client.aclose.assert_called_once()

    @pytest.mark.anyio
    async def test_disconnect_when_not_connected(self):
        """Test disconnection when not connected."""
        cache = RedisCache()
        cache.client = None

        # Should not raise error
        await cache.disconnect()


class TestRedisCacheGet:
    """Test cache get operation."""

    @pytest.mark.anyio
    async def test_get_success(self, cache):
        """Test successful cache get."""
        cache.client.get = AsyncMock(return_value="test_value")

        result = await cache.get("test_key")

        assert result == "test_value"
        cache.client.get.assert_called_once_with("test_key")

    @pytest.mark.anyio
    async def test_get_not_found(self, cache):
        """Test cache get when key not found."""
        cache.client.get = AsyncMock(return_value=None)

        result = await cache.get("nonexistent_key")

        assert result is None

    @pytest.mark.anyio
    async def test_get_not_connected(self):
        """Test cache get when not connected."""
        cache = RedisCache()
        cache.client = None

        with pytest.raises(CacheError):
            await cache.get("test_key")

    @pytest.mark.anyio
    async def test_get_redis_error(self, cache):
        """Test cache get with Redis error."""
        import redis.asyncio as redis

        cache.client.get = AsyncMock(side_effect=redis.RedisError("Get failed"))

        with pytest.raises(CacheError):
            await cache.get("test_key")


class TestRedisCacheSet:
    """Test cache set operation."""

    @pytest.mark.anyio
    async def test_set_success(self, cache):
        """Test successful cache set."""
        cache.client.setex = AsyncMock()

        await cache.set("test_key", "test_value", ttl_seconds=3600)

        cache.client.setex.assert_called_once_with("test_key", 3600, "test_value")

    @pytest.mark.anyio
    async def test_set_without_ttl(self, cache):
        """Test cache set without TTL."""
        cache.client.set = AsyncMock()

        await cache.set("test_key", "test_value")

        cache.client.set.assert_called_once_with("test_key", "test_value")

    @pytest.mark.anyio
    async def test_set_not_connected(self):
        """Test cache set when not connected."""
        cache = RedisCache()
        cache.client = None

        with pytest.raises(CacheError):
            await cache.set("test_key", "test_value")

    @pytest.mark.anyio
    async def test_set_redis_error(self, cache):
        """Test cache set with Redis error."""
        import redis.asyncio as redis

        cache.client.setex = AsyncMock(side_effect=redis.RedisError("Set failed"))

        with pytest.raises(CacheError):
            await cache.set("test_key", "test_value", ttl_seconds=3600)


class TestRedisCacheDelete:
    """Test cache delete operation."""

    @pytest.mark.anyio
    async def test_delete_success(self, cache):
        """Test successful cache delete."""
        cache.client.delete = AsyncMock(return_value=1)

        result = await cache.delete("test_key")

        assert result is True
        cache.client.delete.assert_called_once_with("test_key")

    @pytest.mark.anyio
    async def test_delete_not_found(self, cache):
        """Test cache delete when key not found."""
        cache.client.delete = AsyncMock(return_value=0)

        result = await cache.delete("nonexistent_key")

        assert result is False

    @pytest.mark.anyio
    async def test_delete_not_connected(self):
        """Test cache delete when not connected."""
        cache = RedisCache()
        cache.client = None

        with pytest.raises(CacheError):
            await cache.delete("test_key")

    @pytest.mark.anyio
    async def test_delete_redis_error(self, cache):
        """Test cache delete with Redis error."""
        import redis.asyncio as redis

        cache.client.delete = AsyncMock(side_effect=redis.RedisError("Delete failed"))

        with pytest.raises(CacheError):
            await cache.delete("test_key")


class TestRedisCacheExists:
    """Test cache exists operation."""

    @pytest.mark.anyio
    async def test_exists_true(self, cache):
        """Test cache exists when key exists."""
        cache.client.exists = AsyncMock(return_value=1)

        result = await cache.exists("test_key")

        assert result is True

    @pytest.mark.anyio
    async def test_exists_false(self, cache):
        """Test cache exists when key doesn't exist."""
        cache.client.exists = AsyncMock(return_value=0)

        result = await cache.exists("nonexistent_key")

        assert result is False

    @pytest.mark.anyio
    async def test_exists_not_connected(self):
        """Test cache exists when not connected."""
        cache = RedisCache()
        cache.client = None

        with pytest.raises(CacheError):
            await cache.exists("test_key")


class TestRedisCacheIncrement:
    """Test cache increment operation."""

    @pytest.mark.anyio
    async def test_increment_success(self, cache):
        """Test successful cache increment."""
        cache.client.incrby = AsyncMock(return_value=5)

        result = await cache.increment("counter_key", amount=1)

        assert result == 5
        cache.client.incrby.assert_called_once_with("counter_key", 1)

    @pytest.mark.anyio
    async def test_increment_with_custom_amount(self, cache):
        """Test cache increment with custom amount."""
        cache.client.incrby = AsyncMock(return_value=10)

        result = await cache.increment("counter_key", amount=5)

        assert result == 10
        cache.client.incrby.assert_called_once_with("counter_key", 5)

    @pytest.mark.anyio
    async def test_increment_not_connected(self):
        """Test cache increment when not connected."""
        cache = RedisCache()
        cache.client = None

        with pytest.raises(CacheError):
            await cache.increment("counter_key")

    @pytest.mark.anyio
    async def test_increment_redis_error(self, cache):
        """Test cache increment with Redis error."""
        import redis.asyncio as redis

        cache.client.incrby = AsyncMock(
            side_effect=redis.RedisError("Increment failed")
        )

        with pytest.raises(CacheError):
            await cache.increment("counter_key")


class TestRedisCacheRateLimit:
    """Test rate limiting functionality."""

    @pytest.mark.anyio
    async def test_rate_limit_allowed(self, cache):
        """Test rate limit when request is allowed."""
        cache.client.incr = AsyncMock(return_value=1)
        cache.client.expire = AsyncMock()

        result = await cache.rate_limit(
            "api:user:123", max_requests=50, window_seconds=60
        )

        assert result is True
        cache.client.incr.assert_called_once_with("api:user:123")
        cache.client.expire.assert_called_once_with("api:user:123", 60)

    @pytest.mark.anyio
    async def test_rate_limit_exceeded(self, cache):
        """Test rate limit when limit is exceeded."""
        cache.client.incr = AsyncMock(return_value=51)
        cache.client.expire = AsyncMock()

        result = await cache.rate_limit(
            "api:user:123", max_requests=50, window_seconds=60
        )

        assert result is False

    @pytest.mark.anyio
    async def test_rate_limit_at_boundary(self, cache):
        """Test rate limit at exact boundary."""
        cache.client.incr = AsyncMock(return_value=50)
        cache.client.expire = AsyncMock()

        result = await cache.rate_limit(
            "api:user:123", max_requests=50, window_seconds=60
        )

        assert result is True

    @pytest.mark.anyio
    async def test_rate_limit_not_connected(self):
        """Test rate limit when not connected."""
        cache = RedisCache()
        cache.client = None

        with pytest.raises(CacheError):
            await cache.rate_limit("api:user:123", max_requests=50, window_seconds=60)

    @pytest.mark.anyio
    async def test_rate_limit_redis_error(self, cache):
        """Test rate limit with Redis error."""
        import redis.asyncio as redis

        cache.client.incr = AsyncMock(side_effect=redis.RedisError("Rate limit failed"))

        with pytest.raises(CacheError):
            await cache.rate_limit("api:user:123", max_requests=50, window_seconds=60)


class TestRedisCacheLock:
    """Test distributed lock functionality."""

    @pytest.mark.anyio
    async def test_lock_acquired(self, cache):
        """Test successful lock acquisition."""
        cache.client.set = AsyncMock(return_value=True)
        cache.client.delete = AsyncMock()

        async with cache.lock("workflow:wf-001", timeout_seconds=60) as acquired:
            assert acquired is True

        cache.client.delete.assert_called_once_with("lock:workflow:wf-001")

    @pytest.mark.anyio
    async def test_lock_not_acquired(self, cache):
        """Test lock acquisition failure."""
        cache.client.set = AsyncMock(return_value=False)
        cache.client.delete = AsyncMock()

        async with cache.lock("workflow:wf-001", timeout_seconds=60) as acquired:
            assert acquired is False

        cache.client.delete.assert_not_called()

    @pytest.mark.anyio
    async def test_lock_released_on_exception(self, cache):
        """Test that lock is released even on exception."""
        cache.client.set = AsyncMock(return_value=True)
        cache.client.delete = AsyncMock()

        try:
            async with cache.lock("workflow:wf-001", timeout_seconds=60) as acquired:
                assert acquired is True
                raise ValueError("Test exception")
        except ValueError:
            pass

        cache.client.delete.assert_called_once_with("lock:workflow:wf-001")

    @pytest.mark.anyio
    async def test_lock_not_connected(self):
        """Test lock when not connected."""
        cache = RedisCache()
        cache.client = None

        with pytest.raises(CacheError):
            async with cache.lock("workflow:wf-001"):
                pass

    @pytest.mark.anyio
    async def test_lock_redis_error(self, cache):
        """Test lock with Redis error."""
        import redis.asyncio as redis

        cache.client.set = AsyncMock(side_effect=redis.RedisError("Lock failed"))

        with pytest.raises(CacheError):
            async with cache.lock("workflow:wf-001"):
                pass


class TestRedisCacheSession:
    """Test session management."""

    @pytest.mark.anyio
    async def test_set_session_success(self, cache):
        """Test successful session storage."""
        cache.client.setex = AsyncMock()

        await cache.set_session("session-123", "user-456", ttl_hours=24)

        cache.client.setex.assert_called_once()
        call_args = cache.client.setex.call_args
        assert call_args[0][0] == "session:session-123"
        assert call_args[0][1] == 24 * 3600  # 24 hours in seconds
        assert call_args[0][2] == "user-456"

    @pytest.mark.anyio
    async def test_set_session_custom_ttl(self, cache):
        """Test session storage with custom TTL."""
        cache.client.setex = AsyncMock()

        await cache.set_session("session-123", "user-456", ttl_hours=1)

        cache.client.setex.assert_called_once()
        call_args = cache.client.setex.call_args
        assert call_args[0][1] == 3600  # 1 hour in seconds

    @pytest.mark.anyio
    async def test_get_session_success(self, cache):
        """Test successful session retrieval."""
        cache.client.get = AsyncMock(return_value="user-456")

        result = await cache.get_session("session-123")

        assert result == "user-456"
        cache.client.get.assert_called_once_with("session:session-123")

    @pytest.mark.anyio
    async def test_get_session_not_found(self, cache):
        """Test session retrieval when not found."""
        cache.client.get = AsyncMock(return_value=None)

        result = await cache.get_session("nonexistent-session")

        assert result is None


class TestRedisCacheEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.anyio
    async def test_rate_limit_multiple_requests(self, cache):
        """Test rate limit with multiple sequential requests."""
        cache.client.incr = AsyncMock(side_effect=[1, 2, 3, 4, 5])
        cache.client.expire = AsyncMock()

        for i in range(5):
            result = await cache.rate_limit(
                "api:user:123", max_requests=5, window_seconds=60
            )
            assert result is True

    @pytest.mark.anyio
    async def test_rate_limit_exceeds_after_multiple_requests(self, cache):
        """Test rate limit exceeding after multiple requests."""
        cache.client.incr = AsyncMock(side_effect=[1, 2, 3, 4, 5, 6])
        cache.client.expire = AsyncMock()

        for i in range(5):
            result = await cache.rate_limit(
                "api:user:123", max_requests=5, window_seconds=60
            )
            assert result is True

        result = await cache.rate_limit(
            "api:user:123", max_requests=5, window_seconds=60
        )
        assert result is False

    @pytest.mark.anyio
    async def test_concurrent_locks(self, cache):
        """Test concurrent lock attempts."""
        cache.client.set = AsyncMock(side_effect=[True, False])
        cache.client.delete = AsyncMock()

        # First lock succeeds
        async with cache.lock("workflow:wf-001") as acquired1:
            assert acquired1 is True

            # Second lock fails (simulated)
            cache.client.set = AsyncMock(return_value=False)
            async with cache.lock("workflow:wf-001") as acquired2:
                assert acquired2 is False

    @pytest.mark.anyio
    async def test_cache_with_special_characters_in_key(self, cache):
        """Test cache operations with special characters in key."""
        cache.client.set = AsyncMock()

        await cache.set("user:123:session:2026-01-26", "token_value")

        cache.client.set.assert_called_once()

    @pytest.mark.anyio
    async def test_cache_with_large_value(self, cache):
        """Test cache operations with large values."""
        large_value = "x" * (1024 * 1024)  # 1MB
        cache.client.set = AsyncMock()

        await cache.set("large_key", large_value)

        cache.client.set.assert_called_once()
