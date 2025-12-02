# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Base image with Python and dependencies
# ============================================
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Stage 2: Builder - Install Python dependencies
# ============================================
FROM base as builder

# Install pip and build tools
RUN pip install --upgrade pip hatch

# Copy project files
COPY pyproject.toml ./

# Install dependencies
RUN pip install . --target=/app/deps

# ============================================
# Stage 3: Production image
# ============================================
FROM python:3.11-slim as production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONPATH=/app/deps:/app

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# Copy installed dependencies from builder
COPY --from=builder /app/deps /app/deps

# Copy application code
COPY apps/ ./apps/
COPY shared/ ./shared/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Copy entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "apps.auth.main:app", "--host", "0.0.0.0", "--port", "8000"]
