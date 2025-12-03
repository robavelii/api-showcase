"""File Processor API FastAPI application.

Provides file upload and conversion endpoints with background processing.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from apps.file_processor.config import get_file_processor_settings
from shared.config import get_settings
from shared.exceptions.handlers import register_exception_handlers
from shared.middleware.trusted_hosts import setup_trusted_hosts

settings = get_settings()
file_processor_settings = get_file_processor_settings()

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Uploads",
        "description": "File upload operations including multipart and signed URL uploads.",
    },
    {
        "name": "Files",
        "description": "File conversion and status operations.",
    },
    {
        "name": "Webhooks",
        "description": "Webhook endpoints for conversion completion notifications.",
    },
    {
        "name": "Health",
        "description": "Service health check endpoints.",
    },
]

app = FastAPI(
    title=file_processor_settings.api_title,
    description="""
## File Processor API

A production-ready file processing API with the following features:

- **File Upload**: Upload files via multipart form or get signed URLs for direct upload
- **Format Conversion**: Convert files between formats (PDF, PNG, JPG, WebP, TXT)
- **Background Processing**: Async file conversion using Celery workers
- **Status Tracking**: Real-time conversion status and progress tracking
- **Webhook Notifications**: Receive notifications when conversions complete

### Authentication

This API uses JWT Bearer tokens for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Supported Formats

- **Input**: PDF, PNG, JPEG, GIF, WebP, TXT, CSV, JSON, XML, DOC, DOCX
- **Output**: PDF, PNG, JPG, WebP, TXT
""",
    version=file_processor_settings.api_version,
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

# Include routers
from apps.file_processor.routes import files, uploads, webhooks  # noqa: E402

app.include_router(uploads.router, prefix=file_processor_settings.api_prefix, tags=["Uploads"])
app.include_router(files.router, prefix=file_processor_settings.api_prefix, tags=["Files"])
app.include_router(webhooks.router, prefix=file_processor_settings.api_prefix, tags=["Webhooks"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint.

    Returns service status and dependency health information including
    database and Redis connectivity.
    """
    from shared.health import check_health

    health = await check_health(
        service_name="file-processor-api",
        version=file_processor_settings.api_version,
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
    <title>File Processor API - Stoplight Elements</title>
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
