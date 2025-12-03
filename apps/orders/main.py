"""Orders API FastAPI application.

Provides e-commerce order management and webhook integration endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from apps.orders.config import get_orders_settings
from apps.orders.routes import orders, webhooks
from shared.config import get_settings
from shared.exceptions.handlers import register_exception_handlers
from shared.middleware.trusted_hosts import get_trusted_hosts_middleware

settings = get_settings()
orders_settings = get_orders_settings()

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Orders",
        "description": "Order management operations including CRUD and pagination.",
    },
    {
        "name": "Webhooks",
        "description": "Webhook integration endpoints for payment providers like Stripe.",
    },
    {
        "name": "Health",
        "description": "Service health check endpoints.",
    },
]

app = FastAPI(
    title=orders_settings.api_title,
    description="""
## Orders API

A production-ready e-commerce order management API with the following features:

- **Order Management**: Create, read, update orders with full CRUD support
- **Cursor Pagination**: Efficient pagination for large datasets
- **Filtering & Sorting**: Filter by status, customer, date range; sort by any field
- **Webhook Integration**: Receive and process Stripe payment webhooks
- **Webhook Retry**: Automatic retry with exponential backoff for failed webhooks

### Authentication

This API uses JWT Bearer tokens for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Pagination

This API uses cursor-based pagination. Use the `cursor` parameter with the value from `next_cursor` in the response.
""",
    version=orders_settings.api_version,
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
    app.add_middleware(get_trusted_hosts_middleware(settings.trusted_hosts))

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(orders.router, prefix=orders_settings.api_prefix, tags=["Orders"])
app.include_router(webhooks.router, prefix=orders_settings.api_prefix, tags=["Webhooks"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint.

    Returns service status and dependency health information including
    database and Redis connectivity.
    """
    from shared.health import check_health

    health = await check_health(
        service_name="orders-api",
        version=orders_settings.api_version,
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
        "StripeSignature": {
            "type": "apiKey",
            "in": "header",
            "name": "Stripe-Signature",
            "description": "Stripe webhook signature for payload verification",
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
    <title>Orders API - Stoplight Elements</title>
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
