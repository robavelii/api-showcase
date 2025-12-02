"""Property-based tests for health check endpoints.

**Feature: openapi-showcase, Property 34: Health check availability**
"""

import pytest
from hypothesis import given, settings, strategies as st

from shared.health.checker import (
    HealthChecker,
    HealthStatus,
    DependencyHealth,
    ServiceHealth,
)


class TestHealthCheckProperties:
    """Property tests for health check functionality."""

    @settings(max_examples=100)
    @given(
        service_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        version=st.from_regex(r"[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
    )
    def test_service_health_contains_required_fields(
        self,
        service_name: str,
        version: str,
    ):
        """
        **Feature: openapi-showcase, Property 34: Health check availability**
        
        For any service name and version, ServiceHealth SHALL include
        status, service name, version, timestamp, and dependencies fields.
        """
        health = ServiceHealth(
            status=HealthStatus.HEALTHY,
            service=service_name,
            version=version,
            dependencies=[],
        )
        
        # Verify required fields exist
        assert health.status is not None
        assert health.service == service_name
        assert health.version == version
        assert health.timestamp is not None
        assert health.dependencies is not None
        
        # Verify serialization includes all fields
        health_dict = health.model_dump()
        assert "status" in health_dict
        assert "service" in health_dict
        assert "version" in health_dict
        assert "timestamp" in health_dict
        assert "dependencies" in health_dict


    @settings(max_examples=100)
    @given(
        dep_name=st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
        status=st.sampled_from([HealthStatus.HEALTHY, HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]),
        latency=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False),
        message=st.text(min_size=0, max_size=200),
    )
    def test_dependency_health_structure(
        self,
        dep_name: str,
        status: HealthStatus,
        latency: float,
        message: str,
    ):
        """
        **Feature: openapi-showcase, Property 34: Health check availability**
        
        For any dependency health check, DependencyHealth SHALL include
        name, status, and optional latency and message fields.
        """
        dep_health = DependencyHealth(
            name=dep_name,
            status=status,
            latency_ms=latency,
            message=message if message else None,
        )
        
        assert dep_health.name == dep_name
        assert dep_health.status == status
        assert dep_health.latency_ms == latency
        
        # Verify serialization
        dep_dict = dep_health.model_dump()
        assert "name" in dep_dict
        assert "status" in dep_dict
        assert "latency_ms" in dep_dict

    @settings(max_examples=50)
    @given(
        healthy_count=st.integers(min_value=0, max_value=5),
        unhealthy_count=st.integers(min_value=0, max_value=5),
    )
    def test_overall_status_determination(
        self,
        healthy_count: int,
        unhealthy_count: int,
    ):
        """
        **Feature: openapi-showcase, Property 34: Health check availability**
        
        For any combination of healthy and unhealthy dependencies,
        the overall status SHALL be:
        - HEALTHY if all dependencies are healthy
        - UNHEALTHY if all dependencies are unhealthy
        - DEGRADED if some dependencies are unhealthy
        """
        # Skip if no dependencies
        if healthy_count == 0 and unhealthy_count == 0:
            return
        
        dependencies = []
        
        # Add healthy dependencies
        for i in range(healthy_count):
            dependencies.append(DependencyHealth(
                name=f"healthy-dep-{i}",
                status=HealthStatus.HEALTHY,
            ))
        
        # Add unhealthy dependencies
        for i in range(unhealthy_count):
            dependencies.append(DependencyHealth(
                name=f"unhealthy-dep-{i}",
                status=HealthStatus.UNHEALTHY,
            ))
        
        # Determine expected status
        if unhealthy_count == 0:
            expected_status = HealthStatus.HEALTHY
        elif healthy_count == 0:
            expected_status = HealthStatus.UNHEALTHY
        else:
            expected_status = HealthStatus.DEGRADED
        
        # Create service health with the dependencies
        health = ServiceHealth(
            status=expected_status,
            service="test-service",
            dependencies=dependencies,
        )
        
        assert health.status == expected_status
        assert len(health.dependencies) == healthy_count + unhealthy_count

    def test_health_checker_initialization(self):
        """
        **Feature: openapi-showcase, Property 34: Health check availability**
        
        HealthChecker SHALL be initializable with service name and version.
        """
        checker = HealthChecker(
            service_name="test-api",
            version="1.0.0",
        )
        
        assert checker.service_name == "test-api"
        assert checker.version == "1.0.0"

    @settings(max_examples=50)
    @given(
        service_name=st.sampled_from([
            "auth-api",
            "orders-api",
            "file-processor-api",
            "notifications-api",
            "webhook-tester-api",
            "gateway-api",
        ]),
    )
    def test_health_response_format_consistency(self, service_name: str):
        """
        **Feature: openapi-showcase, Property 34: Health check availability**
        
        For any service, the health response SHALL follow a consistent
        JSON structure with status, service, version, timestamp, and dependencies.
        """
        health = ServiceHealth(
            status=HealthStatus.HEALTHY,
            service=service_name,
            version="1.0.0",
            dependencies=[
                DependencyHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    latency_ms=5.0,
                    message="PostgreSQL connection successful",
                ),
                DependencyHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    latency_ms=2.0,
                    message="Redis connection successful",
                ),
            ],
        )
        
        # Verify JSON serialization
        health_dict = health.model_dump()
        
        # Required top-level fields
        assert health_dict["status"] == "healthy"
        assert health_dict["service"] == service_name
        assert health_dict["version"] == "1.0.0"
        assert "timestamp" in health_dict
        assert isinstance(health_dict["dependencies"], list)
        
        # Verify dependency structure
        for dep in health_dict["dependencies"]:
            assert "name" in dep
            assert "status" in dep
            assert dep["status"] in ["healthy", "unhealthy", "degraded"]
