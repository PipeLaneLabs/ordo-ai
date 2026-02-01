#!/bin/bash
# Run Alembic database migrations for multi-tier agent ecosystem

set -e

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-agent_ecosystem}"
POSTGRES_USER="${POSTGRES_USER:-agent_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-agent_password_secure_123}"
ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-alembic.ini}"
MIGRATION_DIR="${MIGRATION_DIR:-migrations}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Build database URL
build_db_url() {
    echo "postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
}

# Wait for database to be ready
wait_for_database() {
    log_info "Waiting for database to be ready..."
    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if PGPASSWORD="$POSTGRES_PASSWORD" psql \
            -h "$POSTGRES_HOST" \
            -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            -c "SELECT 1" > /dev/null 2>&1; then
            log_info "Database is ready!"
            return 0
        fi

        attempt=$((attempt + 1))
        log_warn "Database not ready yet (attempt $attempt/$max_attempts)..."
        sleep 2
    done

    log_error "Database failed to become ready after $max_attempts attempts"
    return 1
}

# Get current migration version
get_current_version() {
    log_info "Checking current migration version..."

    DB_URL=$(build_db_url)
    export SQLALCHEMY_URL="$DB_URL"

    # Try to get current version, handle case where table doesn't exist
    current_version=$(alembic -c "$ALEMBIC_CONFIG" current 2>/dev/null || echo "None")
    echo "$current_version"
}

# Run migrations
run_migrations() {
    log_info "Running database migrations..."

    DB_URL=$(build_db_url)
    export SQLALCHEMY_URL="$DB_URL"

    # Run alembic upgrade to head
    if alembic -c "$ALEMBIC_CONFIG" upgrade head; then
        log_info "Migrations completed successfully"
        return 0
    else
        log_error "Migration failed"
        return 1
    fi
}

# Show migration history
show_history() {
    log_info "Migration history:"

    DB_URL=$(build_db_url)
    export SQLALCHEMY_URL="$DB_URL"

    alembic -c "$ALEMBIC_CONFIG" history --verbose || log_warn "Could not retrieve migration history"
}

# Rollback to previous version
rollback_migration() {
    local target_version="$1"

    if [ -z "$target_version" ]; then
        log_error "Target version not specified for rollback"
        return 1
    fi

    log_warn "Rolling back to version: $target_version"

    DB_URL=$(build_db_url)
    export SQLALCHEMY_URL="$DB_URL"

    if alembic -c "$ALEMBIC_CONFIG" downgrade "$target_version"; then
        log_info "Rollback completed successfully"
        return 0
    else
        log_error "Rollback failed"
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting database migration process..."

    # Parse command line arguments
    case "${1:-upgrade}" in
        upgrade)
            if ! wait_for_database; then
                log_error "Failed to connect to database"
                exit 1
            fi

            current=$(get_current_version)
            log_info "Current version: $current"

            if ! run_migrations; then
                log_error "Migration process failed"
                exit 1
            fi

            show_history
            log_info "Database migration completed successfully!"
            ;;

        downgrade)
            if [ -z "$2" ]; then
                log_error "Usage: $0 downgrade <target_version>"
                exit 1
            fi

            if ! wait_for_database; then
                log_error "Failed to connect to database"
                exit 1
            fi

            if ! rollback_migration "$2"; then
                exit 1
            fi

            show_history
            ;;

        status)
            if ! wait_for_database; then
                log_error "Failed to connect to database"
                exit 1
            fi

            current=$(get_current_version)
            log_info "Current migration version: $current"
            show_history
            ;;

        *)
            log_error "Unknown command: $1"
            echo "Usage: $0 {upgrade|downgrade|status} [target_version]"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
