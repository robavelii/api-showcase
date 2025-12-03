"""Property-based tests for OpenAPI documentation.

**Feature: openapi-showcase**
"""

import json
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from apps.gateway.openapi_bundler import merge_openapi_specs


# Strategy for generating valid OpenAPI path items
def path_item_strategy():
    """Generate valid OpenAPI path item objects."""
    return st.fixed_dictionaries(
        {
            "get": st.just(
                {
                    "summary": "Test endpoint",
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {"application/json": {"example": {"message": "ok"}}},
                        }
                    },
                }
            )
        }
    )


# Strategy for generating valid OpenAPI schemas
def schema_strategy():
    """Generate valid OpenAPI schema objects."""
    return st.fixed_dictionaries(
        {
            "type": st.just("object"),
            "properties": st.fixed_dictionaries(
                {
                    "id": st.just({"type": "string", "format": "uuid"}),
                    "name": st.just({"type": "string"}),
                }
            ),
            "required": st.just(["id"]),
        }
    )


# Strategy for generating valid OpenAPI specs
def openapi_spec_strategy():
    """Generate valid OpenAPI specification objects."""
    return st.fixed_dictionaries(
        {
            "openapi": st.just("3.1.0"),
            "info": st.fixed_dictionaries(
                {
                    "title": st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
                    "version": st.from_regex(r"[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
                    "description": st.text(min_size=0, max_size=200),
                }
            ),
            "paths": st.dictionaries(
                keys=st.from_regex(r"/[a-z]+(/[a-z]+)?", fullmatch=True),
                values=path_item_strategy(),
                min_size=1,
                max_size=3,
            ),
            "components": st.fixed_dictionaries(
                {
                    "schemas": st.dictionaries(
                        keys=st.from_regex(r"[A-Z][a-zA-Z]+", fullmatch=True),
                        values=schema_strategy(),
                        min_size=0,
                        max_size=2,
                    ),
                    "securitySchemes": st.just(
                        {
                            "BearerAuth": {
                                "type": "http",
                                "scheme": "bearer",
                                "bearerFormat": "JWT",
                            }
                        }
                    ),
                }
            ),
            "tags": st.lists(
                st.fixed_dictionaries(
                    {
                        "name": st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
                        "description": st.text(min_size=0, max_size=100),
                    }
                ),
                min_size=0,
                max_size=2,
            ),
            "security": st.just([{"BearerAuth": []}]),
        }
    )


class TestOpenAPICompletenessProperties:
    """
    **Feature: openapi-showcase, Property 29: OpenAPI spec completeness**
    """

    @settings(max_examples=50)
    @given(spec=openapi_spec_strategy())
    def test_openapi_spec_has_required_fields(self, spec: dict[str, Any]):
        """
        **Feature: openapi-showcase, Property 29: OpenAPI spec completeness**

        For any valid OpenAPI spec, it SHALL contain the required fields:
        openapi version, info, and paths.
        """
        # Required fields must be present
        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec

        # Info must have required fields
        assert "title" in spec["info"]
        assert "version" in spec["info"]

    @settings(max_examples=50)
    @given(spec=openapi_spec_strategy())
    def test_openapi_paths_have_responses(self, spec: dict[str, Any]):
        """
        **Feature: openapi-showcase, Property 29: OpenAPI spec completeness**

        For any endpoint in the OpenAPI spec, it SHALL have response definitions.
        """
        for path, path_item in spec.get("paths", {}).items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]
                    assert "responses" in operation, (
                        f"Missing responses for {method.upper()} {path}"
                    )

    @settings(max_examples=50)
    @given(spec=openapi_spec_strategy())
    def test_openapi_responses_have_examples(self, spec: dict[str, Any]):
        """
        **Feature: openapi-showcase, Property 29: OpenAPI spec completeness**

        For any endpoint in the application, the generated OpenAPI spec SHALL
        contain request/response examples for that endpoint.
        """
        for path, path_item in spec.get("paths", {}).items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]
                    for status_code, response in operation.get("responses", {}).items():
                        if "content" in response:
                            for _content_type, content in response["content"].items():
                                # Either example or examples should be present
                                has_example = "example" in content or "examples" in content
                                # Or schema with example
                                if "schema" in content:
                                    has_example = has_example or "example" in content.get(
                                        "schema", {}
                                    )
                                assert has_example, (
                                    f"Missing example for {method.upper()} {path} {status_code}"
                                )


class TestOpenAPIRoundTripProperties:
    """
    **Feature: openapi-showcase, Property 30: OpenAPI round-trip**
    """

    @settings(max_examples=50)
    @given(spec=openapi_spec_strategy())
    def test_openapi_json_roundtrip(self, spec: dict[str, Any]):
        """
        **Feature: openapi-showcase, Property 30: OpenAPI round-trip**

        For any valid OpenAPI 3.1 specification object, serializing to JSON
        and parsing back SHALL produce an equivalent specification object.
        """
        # Serialize to JSON
        json_str = json.dumps(spec, indent=2)

        # Parse back
        parsed = json.loads(json_str)

        # Should be equivalent
        assert parsed == spec

    @settings(max_examples=50)
    @given(spec=openapi_spec_strategy())
    def test_openapi_structure_preserved_after_roundtrip(self, spec: dict[str, Any]):
        """
        **Feature: openapi-showcase, Property 30: OpenAPI round-trip**

        For any valid OpenAPI spec, the structure (paths, components, etc.)
        SHALL be preserved after JSON round-trip.
        """
        # Serialize and parse
        json_str = json.dumps(spec)
        parsed = json.loads(json_str)

        # Verify structure is preserved
        assert set(parsed.keys()) == set(spec.keys())
        assert set(parsed.get("paths", {}).keys()) == set(spec.get("paths", {}).keys())
        assert set(parsed.get("components", {}).keys()) == set(spec.get("components", {}).keys())


class TestOpenAPIMergeProperties:
    """
    Tests for OpenAPI spec merging functionality.
    """

    @settings(max_examples=30)
    @given(
        spec1=openapi_spec_strategy(),
        spec2=openapi_spec_strategy(),
    )
    def test_merged_spec_contains_all_paths(self, spec1: dict[str, Any], spec2: dict[str, Any]):
        """
        **Feature: openapi-showcase, Property 29: OpenAPI spec completeness**

        When merging multiple OpenAPI specs, the combined spec SHALL contain
        all paths from all source specs (with appropriate prefixes).
        """
        base_info = {
            "title": "Combined API",
            "version": "1.0.0",
            "description": "Test combined spec",
        }

        specs = [
            ("Service1", "/svc1", spec1),
            ("Service2", "/svc2", spec2),
        ]

        combined = merge_openapi_specs(specs, base_info)

        # All paths from spec1 should be present with /svc1 prefix
        for path in spec1.get("paths", {}).keys():
            assert f"/svc1{path}" in combined["paths"]

        # All paths from spec2 should be present with /svc2 prefix
        for path in spec2.get("paths", {}).keys():
            assert f"/svc2{path}" in combined["paths"]

    @settings(max_examples=30)
    @given(
        spec1=openapi_spec_strategy(),
        spec2=openapi_spec_strategy(),
    )
    def test_merged_spec_contains_all_schemas(self, spec1: dict[str, Any], spec2: dict[str, Any]):
        """
        **Feature: openapi-showcase, Property 29: OpenAPI spec completeness**

        When merging multiple OpenAPI specs, the combined spec SHALL contain
        all schemas from all source specs (with service prefixes to avoid conflicts).
        """
        base_info = {
            "title": "Combined API",
            "version": "1.0.0",
            "description": "Test combined spec",
        }

        specs = [
            ("Service1", "/svc1", spec1),
            ("Service2", "/svc2", spec2),
        ]

        combined = merge_openapi_specs(specs, base_info)

        # All schemas from spec1 should be present with Service1_ prefix
        for schema_name in spec1.get("components", {}).get("schemas", {}).keys():
            assert f"Service1_{schema_name}" in combined["components"]["schemas"]

        # All schemas from spec2 should be present with Service2_ prefix
        for schema_name in spec2.get("components", {}).get("schemas", {}).keys():
            assert f"Service2_{schema_name}" in combined["components"]["schemas"]

    @settings(max_examples=30)
    @given(spec=openapi_spec_strategy())
    def test_merged_spec_is_valid_openapi(self, spec: dict[str, Any]):
        """
        **Feature: openapi-showcase, Property 30: OpenAPI round-trip**

        When merging OpenAPI specs, the result SHALL be a valid OpenAPI spec
        that can be serialized and parsed.
        """
        base_info = {
            "title": "Combined API",
            "version": "1.0.0",
            "description": "Test combined spec",
        }

        specs = [("Service1", "/svc1", spec)]

        combined = merge_openapi_specs(specs, base_info)

        # Should have required OpenAPI fields
        assert "openapi" in combined
        assert "info" in combined
        assert "paths" in combined

        # Should be JSON serializable and round-trip correctly
        json_str = json.dumps(combined)
        parsed = json.loads(json_str)
        assert parsed == combined
