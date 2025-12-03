"""Gateway API FastAPI application.

Provides the root API gateway with combined OpenAPI documentation.
"""

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from apps.gateway.config import get_gateway_settings
from apps.gateway.openapi_bundler import create_combined_spec
from shared.config import get_settings
from shared.exceptions.handlers import register_exception_handlers
from shared.middleware.trusted_hosts import setup_trusted_hosts

settings = get_settings()
gateway_settings = get_gateway_settings()

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Documentation",
        "description": "API documentation and OpenAPI specification endpoints.",
    },
    {
        "name": "Health",
        "description": "Service health check endpoints.",
    },
]

app = FastAPI(
    title=gateway_settings.api_title,
    description="""
## OpenAPI Showcase Gateway

The central gateway providing combined documentation for all OpenAPI Showcase services.

### Available Services

| Service | Port | Description |
|---------|------|-------------|
| Auth API | 8001 | Authentication and user management |
| Orders API | 8002 | E-commerce order management |
| File Processor API | 8003 | File upload and conversion |
| Notifications API | 8004 | Real-time notifications |
| Webhook Tester API | 8005 | Webhook testing and inspection |

### Documentation Endpoints

- `/docs` - Swagger UI (this gateway)
- `/redoc` - Redoc documentation
- `/stoplight` - Stoplight Elements
- `/openapi.json` - Combined OpenAPI specification
""",
    version=gateway_settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=None,  # We'll serve our own combined spec
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


async def fetch_openapi_spec(url: str) -> dict | None:
    """Fetch OpenAPI spec from a service.

    Args:
        url: Base URL of the service.

    Returns:
        OpenAPI specification dict or None if fetch fails.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/openapi.json")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None


@app.get(
    "/openapi.json",
    response_class=JSONResponse,
    tags=["Documentation"],
    summary="Combined OpenAPI specification",
    description="Returns a combined OpenAPI 3.1 specification for all services.",
)
async def get_combined_openapi():
    """Get combined OpenAPI specification for all services."""
    # Fetch specs from all services
    auth_spec = await fetch_openapi_spec(gateway_settings.auth_api_url)
    orders_spec = await fetch_openapi_spec(gateway_settings.orders_api_url)
    file_processor_spec = await fetch_openapi_spec(gateway_settings.file_processor_api_url)
    notifications_spec = await fetch_openapi_spec(gateway_settings.notifications_api_url)
    webhook_tester_spec = await fetch_openapi_spec(gateway_settings.webhook_tester_api_url)

    # Create combined spec
    combined = create_combined_spec(
        auth_spec=auth_spec,
        orders_spec=orders_spec,
        file_processor_spec=file_processor_spec,
        notifications_spec=notifications_spec,
        webhook_tester_spec=webhook_tester_spec,
    )

    return JSONResponse(content=combined)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint.

    Returns service status and dependency health information including
    database and Redis connectivity.
    """
    from shared.health import check_health

    health = await check_health(
        service_name="gateway-api",
        version=gateway_settings.api_version,
    )
    return health.model_dump()


# Stoplight Elements documentation
STOPLIGHT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OpenAPI Showcase - Stoplight Elements</title>
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
