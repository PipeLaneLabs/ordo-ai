#!/bin/bash
# Health check script for multi-tier agent ecosystem services

set -e

# Configuration
API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-agent_ecosystem}"
POSTGRES_USER="${POSTGRES_USER:-agent_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-agent_password_secure_123}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
MINIO_HOST="${MINIO_HOST:-localhost}"
MINIO_PORT="${MINIO_PORT:-9000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Logging functions
log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check FastAPI health endpoint
check_api_health() {
    log_info "Checking FastAPI health endpoint..."

    if curl -sf "http://${API_HOST}:${API_PORT}/health" > /dev/null 2>&1; then
        log_pass "FastAPI health check passed"
    else
        log_fail "FastAPI health check failed (http://${API_HOST}:${API_PORT}/health)"
    fi
}

# Check PostgreSQL connectivity
check_postgres() {
    log_info "Checking PostgreSQL connectivity..."

    if PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -c "SELECT 1" > /dev/null 2>&1; then
        log_pass "PostgreSQL connection successful"
    else
        log_fail "PostgreSQL connection failed"
    fi
}

# Check PostgreSQL tables
check_postgres_tables() {
    log_info "Checking PostgreSQL tables..."

    tables=("checkpoints" "workflows" "audit_events")

    for table in "${tables[@]}"; do
        if PGPASSWORD="$POSTGRES_PASSWORD" psql \
            -h "$POSTGRES_HOST" \
            -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            -c "SELECT 1 FROM information_schema.tables WHERE table_name='$table'" \
            2>/dev/null | grep -q "1"; then
            log_pass "Table '$table' exists"
        else
            log_warn "Table '$table' not found (may need migrations)"
        fi
    done
}

# Check Redis connectivity
check_redis() {
    log_info "Checking Redis connectivity..."

    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
        log_pass "Redis connection successful"
    else
        log_fail "Redis connection failed"
    fi
}

# Check MinIO connectivity
check_minio() {
    log_info "Checking MinIO connectivity..."

    if curl -sf "http://${MINIO_HOST}:${MINIO_PORT}/minio/health/ready" > /dev/null 2>&1; then
        log_pass "MinIO health check passed"
    else
        log_fail "MinIO health check failed"
    fi
}

# Check disk space
check_disk_space() {
    log_info "Checking disk space..."

    available=$(df / | awk 'NR==2 {print $4}')
    threshold=$((1024 * 1024))  # 1GB in KB

    if [ "$available" -gt "$threshold" ]; then
        log_pass "Sufficient disk space available ($(numfmt --to=iec $((available * 1024))) free)"
    else
        log_warn "Low disk space ($(numfmt --to=iec $((available * 1024))) free)"
    fi
}

# Check memory usage
check_memory() {
    log_info "Checking memory usage..."

    available=$(free | awk 'NR==2 {print $7}')
    threshold=$((512 * 1024))  # 512MB in KB

    if [ "$available" -gt "$threshold" ]; then
        log_pass "Sufficient memory available ($(numfmt --to=iec $((available * 1024))) free)"
    else
        log_warn "Low memory ($(numfmt --to=iec $((available * 1024))) free)"
    fi
}

# Check required commands
check_dependencies() {
    log_info "Checking required dependencies..."

    commands=("curl" "psql" "redis-cli")

    for cmd in "${commands[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            log_pass "Command '$cmd' is available"
        else
            log_warn "Command '$cmd' is not available"
        fi
    done
}

# Print summary
print_summary() {
    echo ""
    echo "=========================================="
    echo "Health Check Summary"
    echo "=========================================="
    echo -e "${GREEN}Passed:${NC}  $PASSED"
    echo -e "${RED}Failed:${NC}  $FAILED"
    echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
    echo "=========================================="

    if [ $FAILED -gt 0 ]; then
        return 1
    fi

    return 0
}

# Main execution
main() {
    log_info "Starting health checks for multi-tier agent ecosystem..."
    echo ""

    # Check dependencies first
    check_dependencies
    echo ""

    # Check services
    check_api_health
    check_postgres
    check_postgres_tables
    check_redis
    check_minio
    echo ""

    # Check system resources
    check_disk_space
    check_memory
    echo ""

    # Print summary and exit with appropriate code
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
