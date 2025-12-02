# OpenAPI Showcase

[![CI/CD Pipeline](https://github.com/example/openapi-showcase/actions/workflows/ci.yml/badge.svg)](https://github.com/example/openapi-showcase/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/example/openapi-showcase/branch/main/graph/badge.svg)](https://codecov.io/gh/example/openapi-showcase)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade monorepo containing 5 fully documented FastAPI applications demonstrating modern backend development best practices.

## 🚀 One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/example/openapi-showcase)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/openapi-showcase)

[![Deploy to Fly.io](https://img.shields.io/badge/Deploy%20to-Fly.io-purple?style=for-the-badge&logo=fly.io)](https://fly.io/launch?source=https://github.com/example/openapi-showcase)

## 📋 Features

- **5 Production-Ready APIs** - Auth, Orders, File Processor, Notifications, Webhook Tester
- **Complete OpenAPI 3.1 Documentation** - Swagger UI, Redoc, and Stoplight Elements
- **JWT Authentication** - Secure token-based auth with refresh token rotation
- **Background Task Processing** - Celery with Redis for async operations
- **Real-time Communication** - WebSocket and Server-Sent Events support
- **Rate Limiting** - Redis-backed distributed rate limiting
- **Cursor Pagination** - Efficient pagination for large datasets
- **Property-Based Testing** - Comprehensive test suite with Hypothesis

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│              (Web Apps, Mobile Apps, External Services)          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway / Load Balancer                  │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │  Auth   │ │ Orders  │ │  Files  │ │ Notif.  │ │ Webhook │
   │  :8001  │ │  :8002  │ │  :8003  │ │  :8004  │ │  :8005  │
   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │           │           │
        └───────────┴───────────┼───────────┴───────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
             ┌────────────┐          ┌────────────┐
             │ PostgreSQL │          │   Redis    │
             │     16     │          │     7      │
             └────────────┘          └────────────┘
                                           │
                                    ┌──────┴──────┐
                                    ▼             ▼
                              ┌──────────┐  ┌──────────┐
                              │  Celery  │  │  Flower  │
                              │ Workers  │  │  :5555   │
                              └──────────┘  └──────────┘
```

## 📚 API Documentation

Each API provides interactive documentation at multiple endpoints:

| API | Swagger UI | Redoc | Stoplight |
|-----|------------|-------|-----------|
| Auth | [/docs](http://localhost:8001/docs) | [/redoc](http://localhost:8001/redoc) | [/stoplight](http://localhost:8001/stoplight) |
| Orders | [/docs](http://localhost:8002/docs) | [/redoc](http://localhost:8002/redoc) | [/stoplight](http://localhost:8002/stoplight) |
| File Processor | [/docs](http://localhost:8003/docs) | [/redoc](http://localhost:8003/redoc) | [/stoplight](http://localhost:8003/stoplight) |
| Notifications | [/docs](http://localhost:8004/docs) | [/redoc](http://localhost:8004/redoc) | [/stoplight](http://localhost:8004/stoplight) |
| Webhook Tester | [/docs](http://localhost:8005/docs) | [/redoc](http://localhost:8005/redoc) | [/stoplight](http://localhost:8005/stoplight) |


## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Make (optional, for convenience commands)

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/example/openapi-showcase.git
cd openapi-showcase

# Copy environment file
cp .env.example .env

# Start all services
docker compose up --build

# In a new terminal, seed the database with test data
docker compose exec auth-api python scripts/seed_data.py

# Services will be available at:
# - Auth API:          http://localhost:8001
# - Orders API:        http://localhost:8002
# - File Processor:    http://localhost:8003
# - Notifications:     http://localhost:8004
# - Webhook Tester:    http://localhost:8005
# - Flower Dashboard:  http://localhost:5555
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Start PostgreSQL and Redis (using Docker)
docker compose up -d postgres redis

# Run database migrations
alembic upgrade head

# Start individual APIs
uvicorn apps.auth.main:app --reload --port 8001
uvicorn apps.orders.main:app --reload --port 8002
uvicorn apps.file_processor.main:app --reload --port 8003
uvicorn apps.notifications.main:app --reload --port 8004
uvicorn apps.webhook_tester.main:app --reload --port 8005
```

## 🧪 Testing

### Run All Tests

```bash
# Using Make
make test

# Using pytest directly
pytest tests/ -v

# With coverage report
pytest tests/ --cov=apps --cov=shared --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/ -m unit

# Property-based tests only
pytest tests/ -m property

# Integration tests only
pytest tests/ -m integration
```

### Test Each API

```bash
# Test Auth API
pytest tests/properties/test_auth_properties.py -v

# Test Orders API
pytest tests/properties/test_orders_properties.py -v

# Test File Processor API
pytest tests/properties/test_file_processor_properties.py -v

# Test Notifications API
pytest tests/properties/test_notifications_properties.py -v

# Test Webhook Tester API
pytest tests/properties/test_webhook_tester_properties.py -v
```

## 🌱 Seed Data

The project includes a seed script to populate the database with test data for development and testing.

### Running the Seed Script

```bash
# With Docker Compose (recommended)
docker compose exec auth-api python scripts/seed_data.py

# Local development
python scripts/seed_data.py
```

### Test Credentials

After running the seed script, you can use these credentials:

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@example.com | Admin123! |
| User | john.doe@example.com | Password123! |
| User | jane.smith@example.com | Password123! |
| User | bob.wilson@example.com | Password123! |
| User | alice.johnson@example.com | Password123! |

### Seeded Data Overview

The seed script creates:
- **5 Users** - 1 admin and 4 regular users
- **12 Orders** - 3 orders per regular user with various statuses
- **5 Webhook Events** - Sample Stripe and GitHub webhook events
- **5 Files** - Sample uploaded files with conversion jobs
- **12 Notifications** - 3 notifications per regular user
- **2 Webhook Bins** - With 5 captured events each

## 📖 API Usage Examples

### Authentication

```bash
# Register a new user
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!", "full_name": "John Doe"}'

# Login
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'

# Get current user (with token)
curl http://localhost:8001/users/me \
  -H "Authorization: Bearer <access_token>"
```

### Orders API

```bash
# Create an order
curl -X POST http://localhost:8002/orders \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [{"product_id": "prod_123", "quantity": 2, "unit_price": 29.99}],
    "shipping_address": {"street": "123 Main St", "city": "NYC", "zip": "10001"}
  }'

# List orders with pagination
curl "http://localhost:8002/orders?limit=10" \
  -H "Authorization: Bearer <access_token>"

# Filter orders by status
curl "http://localhost:8002/orders?status=pending" \
  -H "Authorization: Bearer <access_token>"
```

### File Processor API

```bash
# Upload a file
curl -X POST http://localhost:8003/uploads \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@document.pdf"

# Request file conversion
curl -X POST http://localhost:8003/files/convert \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"file_id": "<file_uuid>", "target_format": "png"}'

# Check conversion status
curl http://localhost:8003/files/<file_uuid>/status \
  -H "Authorization: Bearer <access_token>"
```

### Notifications API

```bash
# Connect to WebSocket for real-time notifications
websocat "ws://localhost:8004/ws/notifications?token=<access_token>"

# Get notification history
curl http://localhost:8004/notifications \
  -H "Authorization: Bearer <access_token>"

# Send a notification (admin)
curl -X POST http://localhost:8004/notifications \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_ids": ["<user_uuid>"], "title": "Hello", "message": "Test notification"}'
```

### Webhook Tester API

```bash
# Create a webhook bin
curl -X POST http://localhost:8005/bins \
  -H "Authorization: Bearer <access_token>"

# Send a test webhook to the bin
curl -X POST http://localhost:8005/<bin_id> \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "data": {"key": "value"}}'

# List captured events
curl http://localhost:8005/<bin_id>/events \
  -H "Authorization: Bearer <access_token>"
```


## 📁 Project Structure

```
openapi-showcase/
├── apps/                          # Application modules
│   ├── auth/                      # Authentication API
│   │   ├── main.py               # FastAPI app instance
│   │   ├── config.py             # Auth-specific settings
│   │   ├── routes/               # API endpoints
│   │   ├── services/             # Business logic
│   │   ├── models/               # SQLModel definitions
│   │   └── schemas/              # Pydantic schemas
│   ├── orders/                    # E-commerce Orders API
│   ├── file_processor/            # File Processing API
│   ├── notifications/             # Real-time Notifications API
│   ├── webhook_tester/            # Webhook Testing API
│   └── gateway/                   # API Gateway
├── shared/                        # Shared utilities
│   ├── auth/                      # JWT & password utilities
│   ├── database/                  # Database connection
│   ├── pagination/                # Cursor pagination
│   ├── rate_limit/                # Rate limiting
│   ├── middleware/                # CORS, trusted hosts
│   ├── exceptions/                # Error handling
│   └── schemas/                   # Common schemas
├── tests/                         # Test suite
│   ├── properties/                # Property-based tests
│   ├── unit/                      # Unit tests
│   └── integration/               # Integration tests
├── migrations/                    # Alembic migrations
├── docs/                          # Documentation
├── scripts/                       # Utility scripts
├── .github/workflows/             # CI/CD pipelines
├── docker-compose.yml             # Docker services
├── Dockerfile                     # Container build
├── pyproject.toml                 # Project configuration
├── render.yaml                    # Render deployment
├── fly.toml                       # Fly.io deployment
└── railway.json                   # Railway deployment
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/openapi_showcase` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing key | (required in production) |
| `ENVIRONMENT` | Environment name | `development` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token expiry | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | JWT refresh token expiry | `7` |
| `RATE_LIMIT_PER_MINUTE` | Rate limit per IP | `100` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |

## 🛠️ Development Commands

```bash
# Start development environment
make dev

# Run tests
make test

# Run linting
make lint

# Format code
make format

# Run database migrations
make migrate

# Open database shell
make db-shell

# Build Docker images
make build

# Clean up
make clean
```

## 🔒 Security Features

- **JWT Authentication** - Access tokens (15min) and refresh tokens (7 days)
- **Password Hashing** - bcrypt with automatic salt
- **Rate Limiting** - Redis-backed distributed rate limiting
- **CORS Protection** - Configurable allowed origins
- **Trusted Hosts** - Host header validation
- **Webhook Signatures** - HMAC-SHA256 verification

## 📊 Monitoring

- **Health Checks** - `/health` endpoint on each API
- **Flower Dashboard** - Celery task monitoring at `:5555`
- **Structured Logging** - JSON logs for easy parsing
- **Request Tracing** - Request ID propagation

## 📋 Comprehensive API Testing Guide

This section provides detailed instructions for testing each API endpoint.

### Prerequisites for Testing

1. Start all services: `docker compose up --build`
2. Seed the database: `docker compose exec auth-api python scripts/seed_data.py`
3. Get an access token by logging in (see Authentication section below)

### 1. Auth API Testing (Port 8001)

```bash
# Health check
curl http://localhost:8001/health

# Register a new user
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "password": "SecurePass123!", "full_name": "New User"}'

# Login with seeded user
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "john.doe@example.com", "password": "Password123!"}'
# Save the access_token from response

# Get current user profile
curl http://localhost:8001/users/me \
  -H "Authorization: Bearer <access_token>"

# Refresh token
curl -X POST http://localhost:8001/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'

# Logout
curl -X POST http://localhost:8001/auth/logout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

### 2. Orders API Testing (Port 8002)

```bash
# Health check
curl http://localhost:8002/health

# List all orders (requires auth)
curl http://localhost:8002/orders \
  -H "Authorization: Bearer <access_token>"

# List orders with pagination
curl "http://localhost:8002/orders?limit=5" \
  -H "Authorization: Bearer <access_token>"

# Filter orders by status
curl "http://localhost:8002/orders?status=pending" \
  -H "Authorization: Bearer <access_token>"

# Filter orders by date range
curl "http://localhost:8002/orders?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer <access_token>"

# Create a new order
curl -X POST http://localhost:8002/orders \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"product_id": "PROD-001", "product_name": "Widget", "quantity": 2, "unit_price": 29.99}
    ],
    "shipping_address": {"street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001"},
    "billing_address": {"street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001"}
  }'

# Get specific order
curl http://localhost:8002/orders/<order_id> \
  -H "Authorization: Bearer <access_token>"

# Update order status
curl -X PATCH http://localhost:8002/orders/<order_id> \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'

# List webhook events
curl http://localhost:8002/webhooks \
  -H "Authorization: Bearer <access_token>"
```

### 3. File Processor API Testing (Port 8003)

```bash
# Health check
curl http://localhost:8003/health

# Upload a file
curl -X POST http://localhost:8003/uploads \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/your/file.pdf"

# Get signed URL for direct upload
curl -X POST http://localhost:8003/uploads/signed-url \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"filename": "document.pdf", "content_type": "application/pdf"}'

# Request file conversion
curl -X POST http://localhost:8003/files/convert \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"file_id": "<file_uuid>", "target_format": "png"}'

# Check conversion status
curl http://localhost:8003/files/<file_id>/status \
  -H "Authorization: Bearer <access_token>"

# List user's files
curl http://localhost:8003/files \
  -H "Authorization: Bearer <access_token>"
```

### 4. Notifications API Testing (Port 8004)

```bash
# Health check
curl http://localhost:8004/health

# Get notification history
curl http://localhost:8004/notifications \
  -H "Authorization: Bearer <access_token>"

# Get notifications with pagination
curl "http://localhost:8004/notifications?limit=10" \
  -H "Authorization: Bearer <access_token>"

# Send notification (admin only)
curl -X POST http://localhost:8004/notifications \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": ["<user_uuid>"],
    "title": "Test Notification",
    "message": "This is a test notification",
    "type": "info"
  }'

# Mark notification as read
curl -X PATCH http://localhost:8004/notifications/<notification_id>/read \
  -H "Authorization: Bearer <access_token>"

# WebSocket connection (use websocat or similar tool)
websocat "ws://localhost:8004/ws/notifications?token=<access_token>"

# Server-Sent Events connection
curl http://localhost:8004/events \
  -H "Authorization: Bearer <access_token>"
```

### 5. Webhook Tester API Testing (Port 8005)

```bash
# Health check
curl http://localhost:8005/health

# Create a webhook bin
curl -X POST http://localhost:8005/bins \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Test Bin"}'

# List user's bins
curl http://localhost:8005/bins \
  -H "Authorization: Bearer <access_token>"

# Send a test webhook to a bin (no auth required)
curl -X POST http://localhost:8005/<bin_id> \
  -H "Content-Type: application/json" \
  -H "X-Custom-Header: test-value" \
  -d '{"event": "order.created", "data": {"order_id": "12345", "amount": 99.99}}'

# List captured events for a bin
curl http://localhost:8005/<bin_id>/events \
  -H "Authorization: Bearer <access_token>"

# Delete a bin
curl -X DELETE http://localhost:8005/bins/<bin_id> \
  -H "Authorization: Bearer <access_token>"
```

### Testing with Swagger UI

Each API provides interactive Swagger UI documentation:

1. **Auth API**: http://localhost:8001/docs
2. **Orders API**: http://localhost:8002/docs
3. **File Processor API**: http://localhost:8003/docs
4. **Notifications API**: http://localhost:8004/docs
5. **Webhook Tester API**: http://localhost:8005/docs

To test authenticated endpoints in Swagger UI:
1. Click the "Authorize" button
2. Enter your access token in the format: `Bearer <your_token>`
3. Click "Authorize" to save
4. Now you can test protected endpoints

### Running Automated Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=apps --cov=shared --cov-report=html --cov-report=term

# Run specific test file
pytest tests/properties/test_auth_properties.py -v

# Run tests matching a pattern
pytest tests/ -k "test_password" -v

# Run tests with detailed output
pytest tests/ -v --tb=long

# Run tests in parallel (requires pytest-xdist)
pytest tests/ -n auto
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLModel](https://sqlmodel.tiangolo.com/) - SQL databases with Python types
- [Pydantic](https://docs.pydantic.dev/) - Data validation using Python type hints
- [Celery](https://docs.celeryq.dev/) - Distributed task queue
- [Hypothesis](https://hypothesis.readthedocs.io/) - Property-based testing
