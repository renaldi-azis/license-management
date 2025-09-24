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
from models.database import insert_default_users;
insert_default_users()
"

# Start the application
echo "Starting License Management Server..."
exec "$@"