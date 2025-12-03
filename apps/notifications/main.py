"""Notifications API FastAPI application.

Provides real-time notifications via WebSocket and SSE endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from apps.notifications.config import get_notifications_settings
from shared.config import get_settings
from shared.exceptions.handlers import register_exception_handlers
from shared.middleware.trusted_hosts import setup_trusted_hosts

settings = get_settings()
notifications_settings = get_notifications_settings()

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "WebSocket",
        "description": "WebSocket endpoints for real-time notification delivery.",
    },
    {
        "name": "SSE",
        "description": "Server-Sent Events endpoints as WebSocket fallback.",
    },
    {
        "name": "Notifications",
        "description": "Notification management and history operations.",
    },
    {
        "name": "Health",
        "description": "Service health check endpoints.",
    },
]

app = FastAPI(
    title=notifications_settings.api_title,
    description="""
## Notifications API

A production-ready real-time notifications API with the following features:

- **WebSocket**: Real-time bidirectional communication for instant notifications
- **Server-Sent Events**: Fallback for environments that don't support WebSocket
- **Notification History**: Paginated access to past notifications
- **Read Status**: Mark notifications as read
- **Multi-Instance Support**: Redis-backed connection management for horizontal scaling

### Authentication

This API uses JWT Bearer tokens for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

For WebSocket connections, pass the token as a query parameter:

```
ws://host/ws/notifications?token=<access_token>
```

### Real-Time Channels

- **WebSocket**: `ws://host/ws/notifications` - Full duplex communication
- **SSE**: `GET /events` - Server-to-client streaming
""",
    version=notifications_settings.api_version,
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
from apps.notifications.routes import notifications, sse, websocket  # noqa: E402

app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(sse.router, prefix=notifications_settings.api_prefix, tags=["SSE"])
app.include_router(
    notifications.router, prefix=notifications_settings.api_prefix, tags=["Notifications"]
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint.

    Returns service status and dependency health information including
    database and Redis connectivity.
    """
    from shared.health import check_health

    health = await check_health(
        service_name="notifications-api",
        version=notifications_settings.api_version,
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
    <title>Notifications API - Stoplight Elements</title>
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
