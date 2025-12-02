#!/bin/bash
set -e

# Wait for database to be ready (optional, depends on healthcheck)
wait_for_db() {
    echo "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from shared.config import get_settings

async def check():
    settings = get_settings()
    engine = create_async_engine(str(settings.database_url))
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()

from sqlalchemy import text
exit(0 if asyncio.run(check()) else 1)
" 2>/dev/null; then
            echo "Database is ready!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: Database not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "Warning: Could not verify database connection after $max_attempts attempts"
    return 1
}

# Run database migrations if APPLY_MIGRATIONS is set
if [ "$APPLY_MIGRATIONS" = "true" ]; then
    echo "Checking database connection..."
    wait_for_db || true
    
    echo "Applying database migrations..."
    python -m alembic upgrade head
    
    if [ $? -eq 0 ]; then
        echo "Migrations applied successfully!"
    else
        echo "Warning: Migration failed, but continuing startup..."
    fi
fi

# Execute the main command
exec "$@"
