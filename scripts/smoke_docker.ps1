# SmartDesk AI - Docker & PostgreSQL End-to-End Smoke Test (scripts/smoke_docker.ps1)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/smoke_docker.ps1 [-KeepRunning]
#
# Requirements tested:
#   - REQ-07: Docker Compose orchestrating postgres (pgvector), backend (FastAPI), frontend (Nginx)
#   - REQ-11: PostgreSQL 16 with pgvector extension verification
#   - REQ-06 / REQ-36: Demo authentication and JWT issuance
#   - REQ-30 / REQ-31: Ticket listing and X-Total-Count header via API

param (
    [switch]$KeepRunning = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  SmartDesk AI - Docker Compose & PostgreSQL Smoke Test" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# Step 0: Docker Daemon Check
Write-Host "`n[1/7] Checking Docker Engine availability..." -ForegroundColor Yellow
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker engine is not running or unreachable." -ForegroundColor Red
        Write-Host "Detail: $dockerInfo" -ForegroundColor DarkGray
        Write-Host "Please start Docker Desktop and ensure the Linux engine is active before running this smoke test." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Docker Engine is active and ready." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to invoke docker command. Ensure Docker is installed and in PATH." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor DarkGray
    exit 1
}

$cleanupNeeded = $false

try {
    # Step 1: Clean build
    Write-Host "`n[2/7] Building Docker images (postgres, backend, frontend)..." -ForegroundColor Yellow
    docker compose build
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose build failed with exit code $LASTEXITCODE"
    }
    Write-Host "Build completed successfully." -ForegroundColor Green

    # Step 2: Start services
    Write-Host "`n[3/7] Starting containers in detached mode..." -ForegroundColor Yellow
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up -d failed with exit code $LASTEXITCODE"
    }
    $cleanupNeeded = $true
    Write-Host "Containers started. Waiting for service healthchecks..." -ForegroundColor Green

    # Step 3: Poll backend health
    Write-Host "`n[4/7] Polling backend health (http://localhost:8000/api/v1/health)..." -ForegroundColor Yellow
    $backendHealthy = $false
    $maxAttempts = 30
    for ($i = 1; $i -le $maxAttempts; $i++) {
        try {
            $healthResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get -TimeoutSec 3
            if ($healthResp.status -eq "ok" -or $healthResp.database -eq "connected" -or $healthResp.status -eq "healthy") {
                $backendHealthy = $true
                Write-Host "Backend is healthy (attempt $i/$maxAttempts): status=$($healthResp.status), db=$($healthResp.database)" -ForegroundColor Green
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    if (-not $backendHealthy) {
        docker compose logs backend --tail 30
        throw "Backend failed to become healthy within $($maxAttempts * 2) seconds."
    }

    # Step 4: Verify Nginx frontend & reverse proxy
    Write-Host "`n[5/7] Verifying Nginx frontend and reverse proxy (http://localhost:3000)..." -ForegroundColor Yellow
    $frontendOk = $false
    for ($i = 1; $i -le 15; $i++) {
        try {
            $frontResp = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 3
            if ($frontResp.StatusCode -eq 200) {
                $proxyResp = Invoke-RestMethod -Uri "http://localhost:3000/api/v1/health" -Method Get -TimeoutSec 3
                if ($proxyResp.status -eq "ok" -or $proxyResp.database -eq "connected") {
                    $frontendOk = $true
                    Write-Host "Frontend SPA (HTTP 200) and reverse proxy /api/v1/ are functional!" -ForegroundColor Green
                    break
                }
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    if (-not $frontendOk) {
        docker compose logs frontend --tail 30
        throw "Frontend or Nginx API reverse proxy failed verification."
    }

    # Step 5: Test Demo Authentication & Ticket Listing
    Write-Host "`n[6/7] Testing demo authentication and authenticated API access..." -ForegroundColor Yellow
    $loginBody = @{
        provider = "demo"
        email = "admin@smartdesk.local"
    } | ConvertTo-Json

    $loginResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/oauth2/login" `
        -Method Post `
        -ContentType "application/json" `
        -Body $loginBody `
        -TimeoutSec 5

    if (-not $loginResp.access_token) {
        throw "Demo login succeeded but returned no access_token!"
    }
    Write-Host "Authentication successful: token issued for $($loginResp.user.email) (role=$($loginResp.user.role))" -ForegroundColor Green

    $authHeader = @{
        "Authorization" = "Bearer $($loginResp.access_token)"
    }
    $ticketResp = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/tickets" `
        -Method Get `
        -Headers $authHeader `
        -UseBasicParsing `
        -TimeoutSec 5

    $totalCount = $ticketResp.Headers["X-Total-Count"]
    Write-Host "Ticket listing successful: HTTP $($ticketResp.StatusCode), X-Total-Count=$totalCount" -ForegroundColor Green

    # Step 6: Verify PostgreSQL pgvector extension in container
    Write-Host "`n[7/7] Verifying pgvector extension in PostgreSQL container..." -ForegroundColor Yellow
    $vectorCheck = docker compose exec -T postgres psql -U postgres -d smartdesk -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';" 2>&1
    if ($vectorCheck -match "vector") {
        Write-Host "pgvector extension verified in PostgreSQL database:" -ForegroundColor Green
        Write-Host $vectorCheck -ForegroundColor DarkGray
    } else {
        throw "pgvector extension not found in PostgreSQL! Output: $vectorCheck"
    }

    Write-Host "`n=================================================================" -ForegroundColor Green
    Write-Host "  ALL DOCKER & POSTGRESQL SMOKE CHECKS PASSED!" -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor Green

} catch {
    Write-Host "`nSMOKE TEST FAILED: $_" -ForegroundColor Red
    exit 1
} finally {
    if ($cleanupNeeded -and -not $KeepRunning) {
        Write-Host "`nTearing down containers and volumes (--remove-orphans -v)..." -ForegroundColor Yellow
        docker compose down -v --remove-orphans
        Write-Host "Teardown complete." -ForegroundColor Green
    } elseif ($KeepRunning) {
        Write-Host "`nKeeping containers running as requested (-KeepRunning)." -ForegroundColor Cyan
    }
}
