"""Property-based tests for CORS middleware.

**Feature: openapi-showcase**
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from shared.middleware.cors import setup_cors

# Strategy for generating valid origin URLs
origin_strategy = st.builds(
    lambda scheme, domain, port: f"{scheme}://{domain}" + (f":{port}" if port else ""),
    scheme=st.sampled_from(["http", "https"]),
    domain=st.from_regex(r"[a-z][a-z0-9]{2,15}\.(com|org|net|io)", fullmatch=True),
    port=st.one_of(st.none(), st.integers(min_value=1000, max_value=9999).map(str)),
)


def create_test_app(allowed_origins: list[str]) -> FastAPI:
    """Create a test FastAPI app with CORS configured."""
    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    setup_cors(app, origins=allowed_origins)
    return app


class TestCORSEnforcementProperties:
    """
    **Feature: openapi-showcase, Property 33: CORS enforcement**
    """

    @settings(max_examples=100)
    @given(
        allowed_origin=origin_strategy,
    )
    def test_allowed_origin_receives_cors_header(self, allowed_origin: str):
        """
        **Feature: openapi-showcase, Property 33: CORS enforcement**

        For any request from an allowed origin, the response SHALL include
        Access-Control-Allow-Origin header matching that origin.
        """
        app = create_test_app(allowed_origins=[allowed_origin])
        client = TestClient(app)

        # Make a request with the allowed origin
        response = client.get("/test", headers={"Origin": allowed_origin})

        # Should include CORS header for allowed origin
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == allowed_origin

    @settings(max_examples=100)
    @given(
        allowed_origin=origin_strategy,
        request_origin=origin_strategy,
    )
    def test_non_allowed_origin_does_not_receive_cors_header(
        self, allowed_origin: str, request_origin: str
    ):
        """
        **Feature: openapi-showcase, Property 33: CORS enforcement**

        For any request from a non-allowed origin, the response SHALL NOT include
        Access-Control-Allow-Origin header for that origin.
        """
        # Ensure the request origin is different from allowed origin
        assume(request_origin != allowed_origin)

        app = create_test_app(allowed_origins=[allowed_origin])
        client = TestClient(app)

        # Make a request with a non-allowed origin
        response = client.get("/test", headers={"Origin": request_origin})

        # Response should succeed but NOT include CORS header for the non-allowed origin
        assert response.status_code == 200
        cors_header = response.headers.get("access-control-allow-origin")
        # Either no header, or header doesn't match the request origin
        assert cors_header is None or cors_header != request_origin

    @settings(max_examples=50)
    @given(
        origins=st.lists(origin_strategy, min_size=1, max_size=5, unique=True),
    )
    def test_multiple_allowed_origins_each_receives_header(self, origins: list[str]):
        """
        **Feature: openapi-showcase, Property 33: CORS enforcement**

        For any set of allowed origins, each allowed origin SHALL receive
        the Access-Control-Allow-Origin header when making requests.
        """
        app = create_test_app(allowed_origins=origins)
        client = TestClient(app)

        # Each allowed origin should receive CORS header
        for origin in origins:
            response = client.get("/test", headers={"Origin": origin})
            assert response.status_code == 200
            assert response.headers.get("access-control-allow-origin") == origin

    @settings(max_examples=50)
    @given(
        allowed_origin=origin_strategy,
    )
    def test_preflight_request_for_allowed_origin(self, allowed_origin: str):
        """
        **Feature: openapi-showcase, Property 33: CORS enforcement**

        For any preflight (OPTIONS) request from an allowed origin, the response
        SHALL include appropriate CORS headers.
        """
        app = create_test_app(allowed_origins=[allowed_origin])
        client = TestClient(app)

        # Make a preflight request
        response = client.options(
            "/test",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "GET",
            },
        )

        # Preflight should succeed with CORS headers
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == allowed_origin

    @settings(max_examples=50)
    @given(
        allowed_origin=origin_strategy,
        request_origin=origin_strategy,
    )
    def test_preflight_request_for_non_allowed_origin(
        self, allowed_origin: str, request_origin: str
    ):
        """
        **Feature: openapi-showcase, Property 33: CORS enforcement**

        For any preflight (OPTIONS) request from a non-allowed origin, the response
        SHALL NOT include Access-Control-Allow-Origin header for that origin.
        """
        assume(request_origin != allowed_origin)

        app = create_test_app(allowed_origins=[allowed_origin])
        client = TestClient(app)

        # Make a preflight request from non-allowed origin
        response = client.options(
            "/test",
            headers={
                "Origin": request_origin,
                "Access-Control-Request-Method": "GET",
            },
        )

        # Should not include CORS header for non-allowed origin
        cors_header = response.headers.get("access-control-allow-origin")
        assert cors_header is None or cors_header != request_origin
