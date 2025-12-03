"""Integration tests for middleware utilities.

Tests CORS and trusted hosts middleware configuration.
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.middleware.cors import get_cors_origins, setup_cors
from shared.middleware.trusted_hosts import (
    get_trusted_hosts,
    get_trusted_hosts_middleware,
    setup_trusted_hosts,
)


class TestCorsMiddleware:
    """Tests for CORS middleware configuration."""

    def test_setup_cors_with_default_origins(self):
        """Test CORS setup with default origins from settings."""
        app = FastAPI()

        with patch("shared.middleware.cors.get_settings") as mock_settings:
            mock_settings.return_value.cors_origins = ["http://localhost:3000"]
            mock_settings.return_value.cors_allow_credentials = True
            mock_settings.return_value.cors_allow_methods = ["*"]
            mock_settings.return_value.cors_allow_headers = ["*"]

            setup_cors(app)

        # Verify middleware was added
        assert len(app.user_middleware) > 0

    def test_setup_cors_with_custom_origins(self):
        """Test CORS setup with custom origins."""
        app = FastAPI()
        custom_origins = ["https://example.com", "https://api.example.com"]

        with patch("shared.middleware.cors.get_settings") as mock_settings:
            mock_settings.return_value.cors_allow_credentials = True
            mock_settings.return_value.cors_allow_methods = ["*"]
            mock_settings.return_value.cors_allow_headers = ["*"]

            setup_cors(app, origins=custom_origins)

        assert len(app.user_middleware) > 0

    def test_cors_allows_configured_origin(self):
        """Test that CORS allows requests from configured origins."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        with patch("shared.middleware.cors.get_settings") as mock_settings:
            mock_settings.return_value.cors_origins = ["http://localhost:3000"]
            mock_settings.return_value.cors_allow_credentials = True
            mock_settings.return_value.cors_allow_methods = ["*"]
            mock_settings.return_value.cors_allow_headers = ["*"]

            setup_cors(app)

        client = TestClient(app)
        response = client.options(
            "/test",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_get_cors_origins(self):
        """Test getting CORS origins from settings."""
        with patch("shared.middleware.cors.get_settings") as mock_settings:
            mock_settings.return_value.cors_origins = ["http://test.com"]

            origins = get_cors_origins()

            assert origins == ["http://test.com"]


class TestTrustedHostsMiddleware:
    """Tests for trusted hosts middleware configuration."""

    def test_setup_trusted_hosts_with_default_hosts(self):
        """Test trusted hosts setup with default hosts from settings."""
        app = FastAPI()

        with patch("shared.middleware.trusted_hosts.get_settings") as mock_settings:
            mock_settings.return_value.trusted_hosts = ["localhost", "127.0.0.1"]

            setup_trusted_hosts(app)

        # Middleware should be added for specific hosts
        assert len(app.user_middleware) > 0

    def test_setup_trusted_hosts_with_custom_hosts(self):
        """Test trusted hosts setup with custom hosts."""
        app = FastAPI()
        custom_hosts = ["api.example.com", "www.example.com"]

        setup_trusted_hosts(app, hosts=custom_hosts)

        assert len(app.user_middleware) > 0

    def test_setup_trusted_hosts_skips_wildcard(self):
        """Test that wildcard hosts don't add middleware."""
        app = FastAPI()

        with patch("shared.middleware.trusted_hosts.get_settings") as mock_settings:
            mock_settings.return_value.trusted_hosts = ["*"]

            setup_trusted_hosts(app)

        # Middleware should not be added for wildcard
        assert len(app.user_middleware) == 0

    def test_setup_trusted_hosts_skips_empty(self):
        """Test that empty hosts don't add middleware."""
        app = FastAPI()

        with patch("shared.middleware.trusted_hosts.get_settings") as mock_settings:
            mock_settings.return_value.trusted_hosts = []

            setup_trusted_hosts(app)

        assert len(app.user_middleware) == 0

    def test_get_trusted_hosts_middleware_class(self):
        """Test getting configured middleware class."""
        hosts = ["example.com"]

        middleware_class = get_trusted_hosts_middleware(hosts)

        assert middleware_class is not None

    def test_get_trusted_hosts(self):
        """Test getting trusted hosts from settings."""
        with patch("shared.middleware.trusted_hosts.get_settings") as mock_settings:
            mock_settings.return_value.trusted_hosts = ["localhost"]

            hosts = get_trusted_hosts()

            assert hosts == ["localhost"]

    def test_trusted_hosts_rejects_untrusted_host(self):
        """Test that untrusted hosts are rejected."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        setup_trusted_hosts(app, hosts=["trusted.com"])

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test", headers={"Host": "untrusted.com"})

        assert response.status_code == 400

    def test_trusted_hosts_allows_trusted_host(self):
        """Test that trusted hosts are allowed."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        setup_trusted_hosts(app, hosts=["testserver"])

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
