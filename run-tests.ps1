# ============================================================================
# Test Runner Script
# ============================================================================
# Automatically switches to test environment and runs tests

param(
    [string]$TestPath = "tests/",
    [switch]$Coverage,
    [switch]$Verbose,
    [int]$MaxFail = 0
)

Write-Host "🧪 Test Runner - Multi-Tier Agent Ecosystem" -ForegroundColor Cyan
Write-Host ""

# Switch to test environment
Write-Host "Switching to test environment..." -ForegroundColor Yellow
.\switch-env.ps1 test

# Build pytest command
$pytestCmd = "pytest $TestPath"

if ($Verbose) {
    $pytestCmd += " -v"
}

if ($Coverage) {
    $pytestCmd += " --cov=src --cov-report=term-missing --cov-report=html"
}

if ($MaxFail -gt 0) {
    $pytestCmd += " --maxfail=$MaxFail"
}

# Generate timestamped output file
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile = "test_results_$timestamp.txt"

Write-Host ""
Write-Host "Running: $pytestCmd" -ForegroundColor Green
Write-Host "Output will be saved to: $outputFile" -ForegroundColor Cyan
Write-Host ""

# Run tests and save output
Invoke-Expression "$pytestCmd | Tee-Object -FilePath $outputFile"
$testExitCode = $LASTEXITCODE

Write-Host ""
if ($testExitCode -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "❌ Tests failed with exit code: $testExitCode" -ForegroundColor Red
}

# Switch back to development environment
Write-Host ""
Write-Host "Switching back to development environment..." -ForegroundColor Yellow
.\switch-env.ps1 development

exit $testExitCode
