#!/bin/bash

set -e

echo "Running database migrations..."

MIGRATIONS_DIR="migrations"
DB_URL=$(grep DATABASE_URL .env | cut -d '=' -f2- | tr -d '"')

if [ -z "$DB_URL" ]; then
    echo "No DATABASE_URL found in .env"
    exit 1
fi

# SQLite migrations
if [[ "$DB_URL" == sqlite* ]]; then
    DB_PATH="${DB_URL#sqlite://}"
    for migration in "$MIGRATIONS_DIR"/*.sql; do
        if [ -f "$migration" ]; then
            echo "Applying migration: $(basename "$migration")"
            sqlite3 "$DB_PATH" < "$migration"
            echo "$(basename "$migration") applied"
        fi
    done
fi

# PostgreSQL migrations
if [[ "$DB_URL" == postgresql* ]]; then
    for migration in "$MIGRATIONS_DIR"/*.sql; do
        if [ -f "$migration" ]; then
            echo "Applying migration: $(basename "$migration")"
            PGPASSWORD=$(grep DATABASE_PASSWORD .env | cut -d '=' -f2- | tr -d '"') \
            psql "$DB_URL" -v ON_ERROR_STOP=1 -f "$migration"
            echo "$(basename "$migration") applied"
        fi
    done
fi

echo "All migrations completed."
echo "Database schema is up to date."