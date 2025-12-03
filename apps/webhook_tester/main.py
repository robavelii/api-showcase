"""Webhook Tester API FastAPI application.

Provides webhook bin creation and event inspection endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from apps.webhook_tester.config import get_webhook_tester_settings
from shared.config import get_settings
from shared.exceptions.handlers import register_exception_handlers
from shared.middleware.trusted_hosts import setup_trusted_hosts

settings = get_settings()
webhook_tester_settings = get_webhook_tester_settings()

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Bins",
        "description": "Webhook bin management operations.",
    },
    {
        "name": "Events",
        "description": "Webhook event capture and inspection operations.",
    },
    {
        "name": "Health",
        "description": "Service health check endpoints.",
    },
]

app = FastAPI(
    title=webhook_tester_settings.api_title,
    description="""
## Webhook Tester API

A production-ready webhook testing API with the following features:

- **Webhook Bins**: Create unique endpoints to receive webhooks
- **Request Capture**: Capture all HTTP request details (headers, body, metadata)
- **Real-Time Updates**: WebSocket streaming of new webhook events
- **Event History**: Paginated access to captured webhook events
- **Event Replay**: Replay captured webhooks to test endpoints

### Authentication

This API uses JWT Bearer tokens for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Usage

1. Create a webhook bin: `POST /bins`
2. Use the bin URL as your webhook endpoint: `POST /{bin_id}`
3. View captured events: `GET /{bin_id}/events`
4. Stream events in real-time via WebSocket
""",
    version=webhook_tester_settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add trusted hosts middleware
if settings.is_production:
    setup_trusted_hosts(app, settings.trusted_hosts)

# Register exception handlers
register_exception_handlers(app)

# Include routers - imported after app creation to avoid circular imports
from apps.webhook_tester.routes import bins, events  # noqa: E402

app.include_router(bins.router, prefix=webhook_tester_settings.api_prefix, tags=["Bins"])
app.include_router(events.router, tags=["Events"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint.

    Returns service status and dependency health information including
    database and Redis connectivity.
    """
    from shared.health import check_health

    health = await check_health(
        service_name="webhook-tester-api",
        version=webhook_tester_settings.api_version,
    )
    return health.model_dump()


def custom_openapi():
    """Generate custom OpenAPI schema with security schemes."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=tags_metadata,
    )

    # Add security schemes
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token for user authentication",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service authentication",
        },
    }

    # Replace HTTPBearer with BearerAuth in all paths
    for path_data in openapi_schema.get("paths", {}).values():
        for operation in path_data.values():
            if isinstance(operation, dict) and "security" in operation:
                new_security = []
                for sec in operation["security"]:
                    if "HTTPBearer" in sec:
                        new_security.append({"BearerAuth": []})
                    else:
                        new_security.append(sec)
                operation["security"] = new_security

    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}, {"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Stoplight Elements documentation
STOPLIGHT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Webhook Tester API - Stoplight Elements</title>
    <link rel="stylesheet" href="https://unpkg.com/@stoplight/elements/styles.min.css">
    <script src="https://unpkg.com/@stoplight/elements/web-components.min.js"></script>
    <style>
        html, body { height: 100%; margin: 0; padding: 0; }
    </style>
</head>
<body>
    <elements-api
        apiDescriptionUrl="/openapi.json"
        router="hash"
        layout="sidebar"
    />
</body>
</html>
"""


@app.get("/stoplight", response_class=HTMLResponse, include_in_schema=False)
async def stoplight_docs():
    """Serve Stoplight Elements documentation."""
    return STOPLIGHT_HTML
