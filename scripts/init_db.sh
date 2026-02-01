#!/bin/bash
# Initialize PostgreSQL database for multi-tier agent ecosystem
# This script creates the database and required extensions

set -e

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-agent_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-agent_password_secure_123}"
POSTGRES_DB="${POSTGRES_DB:-agent_ecosystem}"
POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-postgres}"
POSTGRES_ADMIN_PASSWORD="${POSTGRES_ADMIN_PASSWORD:-postgres_admin_password}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."
    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" psql \
            -h "$POSTGRES_HOST" \
            -p "$POSTGRES_PORT" \
            -U "$POSTGRES_ADMIN_USER" \
            -d "postgres" \
            -c "SELECT 1" > /dev/null 2>&1; then
            log_info "PostgreSQL is ready!"
            return 0
        fi

        attempt=$((attempt + 1))
        log_warn "PostgreSQL not ready yet (attempt $attempt/$max_attempts)..."
        sleep 2
    done

    log_error "PostgreSQL failed to start after $max_attempts attempts"
    return 1
}

# Create database if it doesn't exist
create_database() {
    log_info "Creating database '$POSTGRES_DB'..."

    PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_ADMIN_USER" \
        -d "postgres" \
        -c "CREATE DATABASE $POSTGRES_DB ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8';" \
        2>/dev/null || log_warn "Database '$POSTGRES_DB' already exists"

    log_info "Database '$POSTGRES_DB' is ready"
}

# Create extensions
create_extensions() {
    log_info "Creating PostgreSQL extensions..."

    PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_ADMIN_USER" \
        -d "$POSTGRES_DB" \
        -c "CREATE EXTENSION IF NOT EXISTS uuid-ossp;" \
        2>/dev/null || log_warn "uuid-ossp extension already exists"

    PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_ADMIN_USER" \
        -d "$POSTGRES_DB" \
        -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" \
        2>/dev/null || log_warn "pgcrypto extension already exists"

    log_info "Extensions created successfully"
}

# Create application user if it doesn't exist
create_app_user() {
    log_info "Creating application user '$POSTGRES_USER'..."

    PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_ADMIN_USER" \
        -d "postgres" \
        -c "CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';" \
        2>/dev/null || log_warn "User '$POSTGRES_USER' already exists"

    # Grant privileges
    PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_ADMIN_USER" \
        -d "$POSTGRES_DB" \
        -c "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;"

    log_info "User '$POSTGRES_USER' configured successfully"
}

# Main execution
main() {
    log_info "Starting database initialization..."

    if ! wait_for_postgres; then
        log_error "Failed to connect to PostgreSQL"
        exit 1
    fi

    create_database
    create_extensions
    create_app_user

    log_info "Database initialization completed successfully!"
}

# Run main function
main
