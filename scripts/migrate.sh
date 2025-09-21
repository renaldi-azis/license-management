#!/bin/bash

set -e

echo "🔄 Running database migrations..."

MIGRATIONS_DIR="migrations"
DB_URL=$(grep DATABASE_URL .env | cut -d '=' -f2-)

if [ -z "$DB_URL" ]; then
    echo "No DATABASE_URL found in .env"
    exit 1
fi

# SQLite migrations
if [[ "$DB_URL" == sqlite* ]]; then
    for migration in "$MIGRATIONS_DIR"/*.sql; do
        if [ -f "$migration" ]; then
            echo "Applying migration: $(basename $migration)"
            sqlite3 "${DB_URL#sqlite://}" < "$migration"
            echo "✓ $(basename $migration) applied"
        fi
    done
fi

# PostgreSQL migrations
if [[ "$DB_URL" == postgresql* ]]; then
    # Extract connection details
    psql -c "\c $DB_URL" && \
    for migration in "$MIGRATIONS_DIR"/*.sql; do
        if [ -f "$migration" ]; then
            echo "Applying migration: $(basename $migration)"
            psql $DB_URL -f "$migration"
            echo "✓ $(basename $migration) applied"
        fi
    done
fi

echo "✅ All migrations completed!"
echo "Database schema is up to date."