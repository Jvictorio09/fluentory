# Script to start PostgreSQL using Docker
# Requires Docker Desktop to be installed and running

Write-Host "=== Starting PostgreSQL with Docker ===" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is available
$dockerAvailable = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerAvailable) {
    Write-Host "ERROR: Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Docker Desktop:" -ForegroundColor Yellow
    Write-Host "  1. Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor White
    Write-Host "  2. Install and start Docker Desktop" -ForegroundColor White
    Write-Host "  3. Ensure Docker Desktop is running (check system tray)" -ForegroundColor White
    Write-Host "  4. Run this script again" -ForegroundColor White
    exit 1
}

# Check if Docker daemon is running
Write-Host "Checking Docker daemon..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "  Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Docker daemon is not running" -ForegroundColor Red
    Write-Host "  Please start Docker Desktop and try again" -ForegroundColor Yellow
    exit 1
}

# Check if container already exists
$existingContainer = docker ps -a --filter "name=fluentory-postgres" --format "{{.Names}}"
if ($existingContainer -eq "fluentory-postgres") {
    Write-Host ""
    Write-Host "Container 'fluentory-postgres' already exists" -ForegroundColor Yellow
    $running = docker ps --filter "name=fluentory-postgres" --format "{{.Names}}"
    if ($running -eq "fluentory-postgres") {
        Write-Host "  Container is already running" -ForegroundColor Green
    } else {
        Write-Host "  Starting existing container..." -ForegroundColor Yellow
        docker start fluentory-postgres
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Container started successfully" -ForegroundColor Green
        } else {
            Write-Host "  Failed to start container" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host ""
    Write-Host "Starting PostgreSQL container..." -ForegroundColor Yellow
    docker-compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Container started successfully" -ForegroundColor Green
    } else {
        Write-Host "  Failed to start container" -ForegroundColor Red
        exit 1
    }
}

# Wait for PostgreSQL to be ready
Write-Host ""
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    Start-Sleep -Seconds 2
    $attempt++
    try {
        $result = docker exec fluentory-postgres pg_isready -U postgres 2>&1
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            Write-Host "  PostgreSQL is ready!" -ForegroundColor Green
        } else {
            Write-Host "  Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
        }
    } catch {
        Write-Host "  Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
    }
}

if (-not $ready) {
    Write-Host "  WARNING: PostgreSQL may not be fully ready yet" -ForegroundColor Yellow
}

# Verify port 5432 is accessible
Write-Host ""
Write-Host "Verifying port 5432..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$portCheck = Test-NetConnection -ComputerName 127.0.0.1 -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
if ($portCheck) {
    Write-Host "  Port 5432 is accessible" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Port 5432 is not accessible yet" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== PostgreSQL is running ===" -ForegroundColor Green
Write-Host ""
Write-Host "Connection details:" -ForegroundColor Cyan
Write-Host "  Host: 127.0.0.1" -ForegroundColor White
Write-Host "  Port: 5432" -ForegroundColor White
Write-Host "  User: postgres" -ForegroundColor White
Write-Host "  Password: postgres" -ForegroundColor White
Write-Host "  Database: fluentory_dev" -ForegroundColor White
Write-Host ""
Write-Host "Your .env file should have:" -ForegroundColor Cyan
Write-Host "  DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/fluentory_dev" -ForegroundColor White
Write-Host ""








