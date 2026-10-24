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
Write-Host "`n[1/8] Checking Docker Engine availability..." -ForegroundColor Yellow
try {
    $dockerVer = docker version
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker engine is not running or unreachable." -ForegroundColor Red
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
    Write-Host "`n[2/8] Building Docker images (postgres, backend, frontend)..." -ForegroundColor Yellow
    docker compose build
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose build failed with exit code $LASTEXITCODE"
    }
    Write-Host "Build completed successfully." -ForegroundColor Green

    # Step 2: Start services
    Write-Host "`n[3/8] Starting containers in detached mode..." -ForegroundColor Yellow
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up -d failed with exit code $LASTEXITCODE"
    }
    $cleanupNeeded = $true
    Write-Host "Containers started. Waiting for service healthchecks..." -ForegroundColor Green

    # Step 3: Poll backend health
    Write-Host "`n[4/8] Polling backend health (http://localhost:8000/api/v1/health)..." -ForegroundColor Yellow
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
    Write-Host "`n[5/8] Verifying Nginx frontend and reverse proxy (http://localhost:3000)..." -ForegroundColor Yellow
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

    # Step 5: Test Demo Authentication & Auth Gates Inside Docker
    Write-Host "`n[6/8] Testing authentication, wrong password (401), and protected route gates..." -ForegroundColor Yellow

    # 5a: Demo admin login works
    $loginBody = @{
        provider = "demo"
        email = "admin@smartdesk.ai"
    } | ConvertTo-Json

    $loginResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/oauth2/login" `
        -Method Post `
        -ContentType "application/json" `
        -Body $loginBody `
        -TimeoutSec 5

    if (-not $loginResp.access_token) {
        throw "Demo login succeeded but returned no access_token!"
    }
    Write-Host "Demo admin login successful: token issued for $($loginResp.email) (role=$($loginResp.role))" -ForegroundColor Green

    # 5b: Wrong password gives 401
    $wrongPasswordOk = $false
    try {
        $wrongPassBody = @{
            username = "admin@smartdesk.ai"
            password = "DefinitivelyWrongPassword2026!"
        } | ConvertTo-Json
        $null = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/token" `
            -Method Post `
            -ContentType "application/json" `
            -Body $wrongPassBody `
            -TimeoutSec 5
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 401) {
            $wrongPasswordOk = $true
            Write-Host "Wrong password rejected with HTTP 401 Unauthorized." -ForegroundColor Green
        } else {
            throw "Wrong password did not return 401: $_"
        }
    }
    if (-not $wrongPasswordOk) {
        throw "Wrong password request unexpectedly succeeded!"
    }

    # 5c: Unauthenticated request to protected route gives 401
    $unauthProtectedOk = $false
    try {
        $dummyTicket = @{
            customer_name = "Unauth User"
            customer_email = "unauth@example.com"
            category = "General"
            priority = "Low"
            subject = "Unauthenticated Attempt"
            description = "This should be blocked."
        } | ConvertTo-Json
        $null = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/tickets" `
            -Method Post `
            -ContentType "application/json" `
            -Body $dummyTicket `
            -TimeoutSec 5
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 401) {
            $unauthProtectedOk = $true
            Write-Host "Unauthenticated request to /tickets rejected with HTTP 401 Unauthorized." -ForegroundColor Green
        } else {
            throw "Unauthenticated request did not return 401: $_"
        }
    }
    if (-not $unauthProtectedOk) {
        throw "Unauthenticated request to /tickets unexpectedly succeeded!"
    }

    # 5d: Authenticated ticket listing works
    $authHeader = @{
        "Authorization" = "Bearer $($loginResp.access_token)"
    }
    $ticketResp = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/tickets" `
        -Method Get `
        -Headers $authHeader `
        -UseBasicParsing `
        -TimeoutSec 5

    $totalCount = $ticketResp.Headers["X-Total-Count"]
    Write-Host "Authenticated ticket listing successful: HTTP $($ticketResp.StatusCode), X-Total-Count=$totalCount" -ForegroundColor Green

    # Step 6: Verify PostgreSQL pgvector extension in container
    Write-Host "`n[7/8] Verifying pgvector extension in PostgreSQL container..." -ForegroundColor Yellow
    $vectorCheck = docker compose exec -T postgres psql -U postgres -d smartdesk -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
    if ($vectorCheck -match "vector") {
        Write-Host "pgvector extension verified in PostgreSQL database:" -ForegroundColor Green
        Write-Host ($vectorCheck -join "`n") -ForegroundColor DarkGray
    } else {
        throw "pgvector extension not found in PostgreSQL! Output: $vectorCheck"
    }

    # Step 7: Verify Nginx proxy buffering configuration for SSE
    Write-Host "`n[8/8] Verifying Nginx reverse proxy buffering for SSE token streaming..." -ForegroundColor Yellow
    $nginxConfig = docker compose exec -T frontend cat /etc/nginx/conf.d/default.conf
    if ($nginxConfig -match "proxy_buffering\s+off;") {
        Write-Host "Nginx proxy_buffering off confirmed for real-time SSE streaming." -ForegroundColor Green
    } else {
        throw "Nginx configuration missing 'proxy_buffering off;' directive!"
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
