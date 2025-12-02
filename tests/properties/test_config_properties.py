"""Property-based tests for configuration.

**Feature: openapi-showcase, Property: Config loading with defaults**
"""

import pytest
from hypothesis import given, settings, strategies as st

from shared.config import Settings


class TestConfigProperties:
    """Property tests for configuration loading."""

    @settings(max_examples=100)
    @given(
        app_env=st.sampled_from(["development", "staging", "production"]),
        debug=st.booleans(),
        pool_size=st.integers(min_value=1, max_value=100),
        max_overflow=st.integers(min_value=0, max_value=100),
        access_token_minutes=st.integers(min_value=1, max_value=1440),
        refresh_token_days=st.integers(min_value=1, max_value=365),
        rate_limit=st.integers(min_value=1, max_value=10000),
    )
    def test_config_accepts_valid_values(
        self,
        app_env: str,
        debug: bool,
        pool_size: int,
        max_overflow: int,
        access_token_minutes: int,
        refresh_token_days: int,
        rate_limit: int,
    ):
        """
        **Feature: openapi-showcase, Property: Config loading with defaults**
        
        For any valid configuration values within constraints,
        Settings SHALL accept and store them correctly.
        """
        config = Settings(
            app_env=app_env,
            debug=debug,
            database_pool_size=pool_size,
            database_max_overflow=max_overflow,
            access_token_expire_minutes=access_token_minutes,
            refresh_token_expire_days=refresh_token_days,
            rate_limit_per_minute=rate_limit,
        )

        assert config.app_env == app_env
        assert config.debug == debug
        assert config.database_pool_size == pool_size
        assert config.database_max_overflow == max_overflow
        assert config.access_token_expire_minutes == access_token_minutes
        assert config.refresh_token_expire_days == refresh_token_days
        assert config.rate_limit_per_minute == rate_limit

    def test_config_uses_sensible_defaults(self, clean_env):
        """
        **Feature: openapi-showcase, Property: Config loading with defaults**
        
        When environment variables are missing,
        Settings SHALL use sensible defaults for local development.
        """
        # Clear the lru_cache to ensure fresh settings
        from shared.config import get_settings
        get_settings.cache_clear()
        
        config = Settings()

        # Verify sensible defaults exist
        assert config.app_name == "OpenAPI Showcase"
        assert config.app_env == "development"
        assert config.debug is True
        assert config.database_pool_size == 5
        assert config.database_max_overflow == 10
        assert config.access_token_expire_minutes == 15
        assert config.refresh_token_expire_days == 7
        assert config.rate_limit_per_minute == 100
        assert config.rate_limit_window_minutes == 15
        assert config.algorithm == "HS256"
        
        # Verify default URLs are set for local development
        assert "localhost" in str(config.database_url)
        assert "localhost" in str(config.redis_url)
        
        # Verify CORS defaults allow local development
        assert "http://localhost:3000" in config.cors_origins
        assert "localhost" in config.trusted_hosts

    @settings(max_examples=50)
    @given(app_env=st.sampled_from(["development", "staging", "production"]))
    def test_environment_properties(self, app_env: str):
        """
        **Feature: openapi-showcase, Property: Config loading with defaults**
        
        For any valid app_env value, the is_production and is_development
        properties SHALL correctly reflect the environment.
        """
        config = Settings(app_env=app_env)

        if app_env == "production":
            assert config.is_production is True
            assert config.is_development is False
        elif app_env == "development":
            assert config.is_production is False
            assert config.is_development is True
        else:  # staging
            assert config.is_production is False
            assert config.is_development is False
