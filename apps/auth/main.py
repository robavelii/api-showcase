"""Auth API FastAPI application.

Provides authentication and user management endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from apps.auth.config import get_auth_settings
from apps.auth.routes import auth, users
from shared.config import get_settings
from shared.exceptions.handlers import register_exception_handlers
from shared.middleware.trusted_hosts import get_trusted_hosts_middleware

settings = get_settings()
auth_settings = get_auth_settings()

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Authentication",
        "description": "User registration, login, token refresh, and logout operations.",
    },
    {
        "name": "Users",
        "description": "User profile management operations.",
    },
    {
        "name": "Health",
        "description": "Service health check endpoints.",
    },
]

app = FastAPI(
    title=auth_settings.api_title,
    description="""
## Auth API

A production-ready authentication API providing JWT-based authentication with the following features:

- **User Registration**: Create new user accounts with email and password
- **User Login**: Authenticate users and issue JWT tokens
- **Token Refresh**: Exchange refresh tokens for new access tokens
- **Token Revocation**: Logout and invalidate tokens
- **User Profile**: View and update user profile information

### Authentication

This API uses JWT Bearer tokens for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Access tokens expire after 15 minutes. Use the refresh token to obtain new access tokens.
""",
    version=auth_settings.api_version,
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
app.include_router(auth.router, prefix=auth_settings.api_prefix, tags=["Authentication"])
app.include_router(users.router, prefix=auth_settings.api_prefix, tags=["Users"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint.
    
    Returns service status and dependency health information including
    database and Redis connectivity.
    """
    from shared.health import check_health
    
    health = await check_health(
        service_name="auth-api",
        version=auth_settings.api_version,
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
            "description": "JWT access token obtained from /auth/login or /auth/register",
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
    <title>Auth API - Stoplight Elements</title>
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
