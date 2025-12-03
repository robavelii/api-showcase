"""Integration tests for health check functionality.

Tests health checker for database and Redis connectivity.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.health.checker import (
    DependencyHealth,
    HealthChecker,
    HealthStatus,
    ServiceHealth,
    check_health,
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        """Test HealthStatus enum values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.DEGRADED == "degraded"


class TestDependencyHealth:
    """Tests for DependencyHealth model."""

    def test_dependency_health_creation(self):
        """Test creating a DependencyHealth instance."""
        health = DependencyHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            latency_ms=5.5,
            message="Connection successful",
        )

        assert health.name == "database"
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms == 5.5
        assert health.message == "Connection successful"

    def test_dependency_health_optional_fields(self):
        """Test DependencyHealth with optional fields."""
        health = DependencyHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
        )

        assert health.latency_ms is None
        assert health.message is None
        assert health.details is None


class TestServiceHealth:
    """Tests for ServiceHealth model."""

    def test_service_health_creation(self):
        """Test creating a ServiceHealth instance."""
        health = ServiceHealth(
            status=HealthStatus.HEALTHY,
            service="auth-api",
            version="1.0.0",
        )

        assert health.status == HealthStatus.HEALTHY
        assert health.service == "auth-api"
        assert health.version == "1.0.0"
        assert health.timestamp is not None
        assert health.dependencies == []

    def test_service_health_with_dependencies(self):
        """Test ServiceHealth with dependencies."""
        db_health = DependencyHealth(
            name="database",
            status=HealthStatus.HEALTHY,
        )
        redis_health = DependencyHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
        )

        health = ServiceHealth(
            status=HealthStatus.HEALTHY,
            service="auth-api",
            dependencies=[db_health, redis_health],
        )

        assert len(health.dependencies) == 2


class TestHealthChecker:
    """Tests for HealthChecker class."""

    @pytest.fixture
    def checker(self):
        """Create a HealthChecker instance."""
        return HealthChecker(service_name="test-service", version="1.0.0")

    @pytest.mark.asyncio
    async def test_check_database_healthy(self, checker):
        """Test database health check when healthy."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        # Create a proper async context manager
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_engine.connect.return_value = mock_cm

        checker.engine = mock_engine

        result = await checker.check_database()

        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms is not None
        assert "successful" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_database_unhealthy(self, checker):
        """Test database health check when unhealthy."""
        mock_engine = AsyncMock()
        mock_engine.connect.side_effect = Exception("Connection refused")
        checker.engine = mock_engine

        result = await checker.check_database()

        assert result.name == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_redis_healthy(self, checker):
        """Test Redis health check when healthy."""
        with patch("shared.health.checker.redis") as mock_redis_module:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_client.close = AsyncMock()
            mock_redis_module.from_url.return_value = mock_client

            result = await checker.check_redis()

            assert result.name == "redis"
            assert result.status == HealthStatus.HEALTHY
            assert "successful" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_redis_unhealthy(self, checker):
        """Test Redis health check when unhealthy."""
        with patch("shared.health.checker.redis") as mock_redis_module:
            mock_redis_module.from_url.side_effect = Exception("Connection refused")

            result = await checker.check_redis()

            assert result.name == "redis"
            assert result.status == HealthStatus.UNHEALTHY
            assert "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_all_healthy(self, checker):
        """Test overall health when all dependencies are healthy."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_engine.connect.return_value = mock_cm
        checker.engine = mock_engine

        with patch("shared.health.checker.redis") as mock_redis_module:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_client.close = AsyncMock()
            mock_redis_module.from_url.return_value = mock_client

            result = await checker.check_all()

            assert result.status == HealthStatus.HEALTHY
            assert result.service == "test-service"
            assert result.version == "1.0.0"
            assert len(result.dependencies) == 2

    @pytest.mark.asyncio
    async def test_check_all_degraded(self, checker):
        """Test overall health when some dependencies are unhealthy."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_engine.connect.return_value = mock_cm
        checker.engine = mock_engine

        with patch("shared.health.checker.redis") as mock_redis_module:
            mock_redis_module.from_url.side_effect = Exception("Connection refused")

            result = await checker.check_all()

            assert result.status == HealthStatus.DEGRADED
            assert len(result.dependencies) == 2

    @pytest.mark.asyncio
    async def test_check_all_unhealthy(self, checker):
        """Test overall health when all dependencies are unhealthy."""
        mock_engine = AsyncMock()
        mock_engine.connect.side_effect = Exception("DB connection refused")
        checker.engine = mock_engine

        with patch("shared.health.checker.redis") as mock_redis_module:
            mock_redis_module.from_url.side_effect = Exception("Redis connection refused")

            result = await checker.check_all()

            assert result.status == HealthStatus.UNHEALTHY


class TestCheckHealthFunction:
    """Tests for the check_health convenience function."""

    @pytest.mark.asyncio
    async def test_check_health_function(self):
        """Test the check_health convenience function."""
        with patch("shared.health.checker.HealthChecker") as MockChecker:
            mock_instance = AsyncMock()
            mock_instance.check_all.return_value = ServiceHealth(
                status=HealthStatus.HEALTHY,
                service="test-service",
            )
            MockChecker.return_value = mock_instance

            result = await check_health("test-service", "2.0.0")

            MockChecker.assert_called_once_with(service_name="test-service", version="2.0.0")
            assert result.status == HealthStatus.HEALTHY
