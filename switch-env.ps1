# ============================================================================
# Environment Switcher Script
# ============================================================================
# Usage: .\switch-env.ps1 <environment>
# Examples:
#   .\switch-env.ps1 development
#   .\switch-env.ps1 docker
#   .\switch-env.ps1 test

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('development', 'docker', 'test', 'production')]
    [string]$Environment
)

$envFile = ".env.$Environment"
$targetFile = ".env"

# Check if source environment file exists
if (-not (Test-Path $envFile)) {
    Write-Host "Error: Environment file '$envFile' not found!" -ForegroundColor Red
    exit 1
}

# Backup current .env if it exists
if (Test-Path $targetFile) {
    $backupFile = ".env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $targetFile $backupFile
    Write-Host "Backed up current .env to $backupFile" -ForegroundColor Yellow
}

# Copy environment file
Copy-Item $envFile $targetFile -Force

Write-Host ""
Write-Host "✅ Switched to $Environment environment" -ForegroundColor Green
Write-Host ""
Write-Host "Active configuration:" -ForegroundColor Cyan
Write-Host "  - Environment: $Environment" -ForegroundColor White
Write-Host "  - Config file: $envFile" -ForegroundColor White
Write-Host ""

# Show relevant commands based on environment
switch ($Environment) {
    'development' {
        Write-Host "Local Development Mode" -ForegroundColor Magenta
        Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor White
        Write-Host "  Redis: localhost:6379" -ForegroundColor White
        Write-Host "  MinIO: localhost:9000" -ForegroundColor White
        Write-Host ""
        Write-Host "Run tests with:" -ForegroundColor Yellow
        Write-Host "  pytest tests/ -v" -ForegroundColor White
        Write-Host ""
        Write-Host "Start dev server:" -ForegroundColor Yellow
        Write-Host "  poetry run uvicorn src.main:app --reload" -ForegroundColor White
    }
    'docker' {
        Write-Host "Docker Deployment Mode" -ForegroundColor Magenta
        Write-Host "  PostgreSQL: postgres:5432 (container)" -ForegroundColor White
        Write-Host "  Redis: redis:6379 (container)" -ForegroundColor White
        Write-Host "  MinIO: minio:9000 (container)" -ForegroundColor White
        Write-Host ""
        Write-Host "Start services with:" -ForegroundColor Yellow
        Write-Host "  docker-compose up -d" -ForegroundColor White
        Write-Host ""
        Write-Host "View logs:" -ForegroundColor Yellow
        Write-Host "  docker-compose logs -f" -ForegroundColor White
    }
    'test' {
        Write-Host "Test Environment Mode" -ForegroundColor Magenta
        Write-Host "  PostgreSQL: localhost:5432 (test DB)" -ForegroundColor White
        Write-Host "  Uses fake API keys" -ForegroundColor White
        Write-Host "  Minimal features enabled" -ForegroundColor White
        Write-Host ""
        Write-Host "Run tests with:" -ForegroundColor Yellow
        Write-Host "  pytest tests/ -v --cov=src" -ForegroundColor White
    }
    'production' {
        Write-Host "⚠️  Production Mode" -ForegroundColor Red
        Write-Host "  Review settings carefully!" -ForegroundColor Yellow
        Write-Host "  Ensure all secrets are updated!" -ForegroundColor Yellow
    }
}

Write-Host ""
