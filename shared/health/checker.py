"""Health check implementation.

Provides health check functionality for database and Redis connectivity.
"""

from datetime import datetime, UTC
from enum import Enum
from typing import Any

import redis.asyncio as redis
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from shared.config import get_settings


class HealthStatus(str, Enum):
    """Health status enumeration."""
    
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class DependencyHealth(BaseModel):
    """Health status for a single dependency."""
    
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] | None = None


class ServiceHealth(BaseModel):
    """Overall service health response."""
    
    status: HealthStatus
    service: str
    version: str = Field(default="1.0.0")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=None))
    dependencies: list[DependencyHealth] = Field(default_factory=list)


class HealthChecker:
    """Health checker for service dependencies."""
    
    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        engine: AsyncEngine | None = None,
    ):
        self.service_name = service_name
        self.version = version
        self.engine = engine
        self.settings = get_settings()

    async def check_database(self) -> DependencyHealth:
        """Check database connectivity."""
        import time
        
        start = time.perf_counter()
        try:
            if self.engine is None:
                from shared.database.connection import get_engine
                self.engine = get_engine()
            
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            
            latency = (time.perf_counter() - start) * 1000
            return DependencyHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
                message="PostgreSQL connection successful",
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return DependencyHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(latency, 2),
                message=f"PostgreSQL connection failed: {str(e)}",
            )

    async def check_redis(self) -> DependencyHealth:
        """Check Redis connectivity."""
        import time
        
        start = time.perf_counter()
        try:
            redis_client = redis.from_url(
                str(self.settings.redis_url),
                encoding="utf-8",
                decode_responses=True,
            )
            await redis_client.ping()
            await redis_client.close()
            
            latency = (time.perf_counter() - start) * 1000
            return DependencyHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
                message="Redis connection successful",
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return DependencyHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(latency, 2),
                message=f"Redis connection failed: {str(e)}",
            )

    async def check_all(self) -> ServiceHealth:
        """Check all dependencies and return overall health status."""
        dependencies = []
        
        # Check database
        db_health = await self.check_database()
        dependencies.append(db_health)
        
        # Check Redis
        redis_health = await self.check_redis()
        dependencies.append(redis_health)
        
        # Determine overall status
        unhealthy_count = sum(
            1 for d in dependencies if d.status == HealthStatus.UNHEALTHY
        )
        
        if unhealthy_count == 0:
            overall_status = HealthStatus.HEALTHY
        elif unhealthy_count == len(dependencies):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        return ServiceHealth(
            status=overall_status,
            service=self.service_name,
            version=self.version,
            dependencies=dependencies,
        )


async def check_health(service_name: str, version: str = "1.0.0") -> ServiceHealth:
    """Convenience function to check health of a service."""
    checker = HealthChecker(service_name=service_name, version=version)
    return await checker.check_all()
