#!/bin/bash
set -e

# Wait for Redis to be ready
if [ "$FLASK_ENV" = "production" ]; then
    echo "Waiting for Redis..."
    until redis-cli -h redis -p 6379 ping; do
        echo "Redis is unavailable - sleeping"
        sleep 2
    done
    echo "Redis is up!"
fi

# Initialize database if it doesn't exist
if [ ! -f /app/data/licenses.db ]; then
    echo "Initializing database..."
    python -c "from models.database import init_db; init_db()"
fi

# Run migrations if they exist
if [ -f /app/migrations/pending.sql ]; then
    echo "Running pending migrations..."
    sqlite3 /app/data/licenses.db < /app/migrations/pending.sql
    rm /app/migrations/pending.sql
fi

# Create admin user if needed
python -c "
from services.security import verify_admin_credentials
if not verify_admin_credentials('admin', 'adminpass'):
    from services.user_service import create_admin_user
    create_admin_user()
"

# Start the application
echo "Starting License Management Server..."
exec "$@"