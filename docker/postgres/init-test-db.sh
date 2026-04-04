#!/bin/bash
set -e

# Create test database alongside the production database
# This script runs automatically on first PostgreSQL container start

TEST_DB="${POSTGRES_DB}_test"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE ${TEST_DB}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${TEST_DB}')\gexec
    GRANT ALL PRIVILEGES ON DATABASE ${TEST_DB} TO ${POSTGRES_USER};
EOSQL

echo "Test database '${TEST_DB}' created successfully."
