"""OpenAPI specification bundler.

Combines multiple OpenAPI specifications into a single unified spec.
"""

import copy
from typing import Any


def merge_openapi_specs(specs: list[dict[str, Any]], base_info: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple OpenAPI specifications into one.
    
    Args:
        specs: List of OpenAPI specification dictionaries with service prefixes.
               Each item should be a tuple of (prefix, spec_dict).
        base_info: Base information for the combined spec (title, version, etc.)
    
    Returns:
        Combined OpenAPI specification dictionary.
    """
    combined = {
        "openapi": "3.1.0",
        "info": base_info,
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {},
        },
        "tags": [],
        "security": [],
    }
    
    seen_security_schemes = set()
    seen_tags = set()
    
    for service_name, prefix, spec in specs:
        if not spec:
            continue
            
        # Merge paths with prefix
        for path, path_item in spec.get("paths", {}).items():
            prefixed_path = f"{prefix}{path}" if prefix else path
            combined["paths"][prefixed_path] = _prefix_refs(
                copy.deepcopy(path_item), 
                service_name
            )
        
        # Merge components/schemas with service prefix to avoid conflicts
        for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
            prefixed_name = f"{service_name}_{schema_name}"
            combined["components"]["schemas"][prefixed_name] = _prefix_refs(
                copy.deepcopy(schema),
                service_name
            )
        
        # Merge security schemes (deduplicate)
        for scheme_name, scheme in spec.get("components", {}).get("securitySchemes", {}).items():
            if scheme_name not in seen_security_schemes:
                combined["components"]["securitySchemes"][scheme_name] = scheme
                seen_security_schemes.add(scheme_name)
        
        # Merge tags with service prefix
        for tag in spec.get("tags", []):
            tag_name = f"{service_name}: {tag['name']}"
            if tag_name not in seen_tags:
                combined["tags"].append({
                    "name": tag_name,
                    "description": tag.get("description", ""),
                })
                seen_tags.add(tag_name)
        
        # Merge security requirements (deduplicate)
        for security in spec.get("security", []):
            if security not in combined["security"]:
                combined["security"].append(security)
    
    return combined


def _prefix_refs(obj: Any, prefix: str) -> Any:
    """Recursively prefix $ref values in an object.
    
    Args:
        obj: Object to process (dict, list, or primitive).
        prefix: Prefix to add to schema references.
    
    Returns:
        Object with prefixed references.
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if key == "$ref" and isinstance(value, str) and value.startswith("#/components/schemas/"):
                # Prefix the schema reference
                schema_name = value.replace("#/components/schemas/", "")
                result[key] = f"#/components/schemas/{prefix}_{schema_name}"
            else:
                result[key] = _prefix_refs(value, prefix)
        return result
    elif isinstance(obj, list):
        return [_prefix_refs(item, prefix) for item in obj]
    else:
        return obj


def create_combined_spec(
    auth_spec: dict[str, Any] | None = None,
    orders_spec: dict[str, Any] | None = None,
    file_processor_spec: dict[str, Any] | None = None,
    notifications_spec: dict[str, Any] | None = None,
    webhook_tester_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a combined OpenAPI specification from all service specs.
    
    Args:
        auth_spec: Auth API OpenAPI spec.
        orders_spec: Orders API OpenAPI spec.
        file_processor_spec: File Processor API OpenAPI spec.
        notifications_spec: Notifications API OpenAPI spec.
        webhook_tester_spec: Webhook Tester API OpenAPI spec.
    
    Returns:
        Combined OpenAPI specification.
    """
    base_info = {
        "title": "OpenAPI Showcase - Combined API",
        "description": """
# OpenAPI Showcase

A production-grade monorepo containing 5 fully documented FastAPI applications demonstrating modern backend development best practices.

## Services

- **Auth API** (`/auth`): JWT authentication, user registration, login, and profile management
- **Orders API** (`/orders`): E-commerce order management with pagination, filtering, and Stripe webhooks
- **File Processor API** (`/files`): File upload and conversion with background processing
- **Notifications API** (`/notifications`): Real-time notifications via WebSocket and SSE
- **Webhook Tester API** (`/webhooks`): Webhook bin creation and event inspection

## Authentication

All APIs use JWT Bearer tokens for authentication:

```
Authorization: Bearer <access_token>
```

## Features

- OpenAPI 3.1 specifications
- Interactive Swagger UI and Redoc documentation
- Cursor-based pagination
- Rate limiting
- Background task processing with Celery
- Real-time communication via WebSocket and SSE
""",
        "version": "1.0.0",
        "contact": {
            "name": "API Support",
            "email": "support@example.com",
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    }
    
    specs = [
        ("Auth", "/auth", auth_spec),
        ("Orders", "/orders", orders_spec),
        ("FileProcessor", "/files", file_processor_spec),
        ("Notifications", "/notifications", notifications_spec),
        ("WebhookTester", "/webhooks", webhook_tester_spec),
    ]
    
    return merge_openapi_specs(specs, base_info)
