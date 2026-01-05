# PostgreSQL Status Check Script for Windows
# This script helps diagnose PostgreSQL connection issues

Write-Host "=== PostgreSQL Connection Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# Check if PostgreSQL service exists
Write-Host "1. Checking for PostgreSQL services..." -ForegroundColor Yellow
$services = Get-Service | Where-Object {$_.DisplayName -like "*PostgreSQL*" -or $_.Name -like "*postgres*"}
if ($services) {
    Write-Host "   Found PostgreSQL services:" -ForegroundColor Green
    $services | Format-Table Name, Status, DisplayName -AutoSize
    
    $running = $services | Where-Object {$_.Status -eq 'Running'}
    if ($running) {
        Write-Host "   PostgreSQL service is RUNNING" -ForegroundColor Green
    } else {
        Write-Host "   PostgreSQL service is NOT RUNNING" -ForegroundColor Red
        Write-Host "   Attempting to start PostgreSQL service..." -ForegroundColor Yellow
        try {
            $service = $services | Select-Object -First 1
            Start-Service -Name $service.Name
            Write-Host "   Service started successfully!" -ForegroundColor Green
        } catch {
            Write-Host "   Failed to start service: $_" -ForegroundColor Red
        }
    }
} else {
    Write-Host "   No PostgreSQL services found" -ForegroundColor Red
    Write-Host "   PostgreSQL may not be installed" -ForegroundColor Yellow
}

Write-Host ""

# Check if port 5432 is accessible
Write-Host "2. Checking port 5432 connectivity..." -ForegroundColor Yellow
$portCheck = Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
if ($portCheck) {
    Write-Host "   Port 5432 is accessible" -ForegroundColor Green
} else {
    Write-Host "   Port 5432 is NOT accessible" -ForegroundColor Red
    Write-Host "   PostgreSQL is likely not running or not listening on port 5432" -ForegroundColor Yellow
}

Write-Host ""

# Check if psql is in PATH
Write-Host "3. Checking for PostgreSQL client (psql)..." -ForegroundColor Yellow
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if ($psqlPath) {
    Write-Host "   psql found at: $($psqlPath.Source)" -ForegroundColor Green
} else {
    Write-Host "   psql not found in PATH" -ForegroundColor Red
    Write-Host "   PostgreSQL client tools may not be installed" -ForegroundColor Yellow
}

Write-Host ""

# Check DATABASE_URL from .env
Write-Host "4. Checking DATABASE_URL configuration..." -ForegroundColor Yellow
if (Test-Path .env) {
    $envContent = Get-Content .env
    $dbUrl = $envContent | Where-Object {$_ -like "DATABASE_URL=*"}
    if ($dbUrl) {
        Write-Host "   DATABASE_URL found in .env" -ForegroundColor Green
        Write-Host "   $dbUrl" -ForegroundColor Gray
    } else {
        Write-Host "   DATABASE_URL not found in .env" -ForegroundColor Red
    }
} else {
    Write-Host "   .env file not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Recommendations ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "If PostgreSQL is not installed:" -ForegroundColor Yellow
Write-Host "  1. Download from: https://www.postgresql.org/download/windows/" -ForegroundColor White
Write-Host "  2. During installation, remember the password you set for postgres user" -ForegroundColor White
Write-Host "  3. Default port is 5432 (keep this unless you change it)" -ForegroundColor White
Write-Host ""
Write-Host "If PostgreSQL is installed but not running:" -ForegroundColor Yellow
Write-Host "  1. Open Services (services.msc)" -ForegroundColor White
Write-Host "  2. Find postgresql-x64-XX service" -ForegroundColor White
Write-Host "  3. Right-click and select Start" -ForegroundColor White
Write-Host ""
Write-Host "To create the database:" -ForegroundColor Yellow
Write-Host "  1. Open pgAdmin or use psql command line" -ForegroundColor White
Write-Host "  2. Connect to PostgreSQL server" -ForegroundColor White
Write-Host "  3. Run: CREATE DATABASE fluentory_dev" -ForegroundColor White
Write-Host ""
