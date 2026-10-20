# SmartDesk AI - Developer Environment Setup Verification Script (verify_setup.ps1)
# Usage in Windows PowerShell:
#   .\scripts\verify_setup.ps1

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  SmartDesk AI - Environment & Toolchain Verification Gate" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$passedSteps = 0
$totalSteps = 8

function Report-Step($stepNum, $stepName, $success, $detail) {
    if ($success) {
        Write-Host "[$stepNum/$totalSteps] PASS - $stepName" -ForegroundColor Green
        if ($detail) { Write-Host "       $detail" -ForegroundColor DarkGray }
        return $true
    } else {
        Write-Host "[$stepNum/$totalSteps] FAIL - $stepName" -ForegroundColor Red
        if ($detail) { Write-Host "       $detail" -ForegroundColor Yellow }
        return $false
    }
}

# Step 1: Git Branch Check
try {
    $branch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($branch) {
        $res = Report-Step 1 "Git Repository & Active Branch" $true "Current branch: $branch"
        $passedSteps++
    } else {
        $res = Report-Step 1 "Git Repository & Active Branch" $false "Could not detect active Git branch"
    }
} catch {
    $res = Report-Step 1 "Git Repository & Active Branch" $false $_.Exception.Message
}

# Step 2: backend/.env Exists and Not Committed
$envPath = "backend/.env"
$envExamplePath = "backend/.env.example"
if (Test-Path $envPath) {
    $rawTracked = git ls-files $envPath
    if ($rawTracked -and "$rawTracked".Trim()) {
        $res = Report-Step 2 "Local Environment File (backend/.env)" $false "CRITICAL: backend/.env is tracked in git! Remove it immediately with git rm --cached."
    } else {
        $res = Report-Step 2 "Local Environment File (backend/.env)" $true "backend/.env exists and is safely untracked"
        $passedSteps++
    }
} else {
    $res = Report-Step 2 "Local Environment File (backend/.env)" $false "backend/.env not found! Copy from ${envExamplePath}: cp backend/.env.example backend/.env"
}

# Step 3: Python 3.11+ and Backend Packages
try {
    $pyCheck = python -c "import sys; import fastapi; import sqlalchemy; import pydantic; import anyio; sys.stdout.write(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($LASTEXITCODE -eq 0 -and $pyCheck) {
        $res = Report-Step 3 "Python & Backend Dependencies" $true "Python $pyCheck with FastAPI, SQLAlchemy, Pydantic verified"
        $passedSteps++
    } else {
        $res = Report-Step 3 "Python & Backend Dependencies" $false "Missing required Python packages. Run: pip install -r backend/requirements.txt"
    }
} catch {
    $res = Report-Step 3 "Python & Backend Dependencies" $false "Python is not installed or not in PATH"
}

# Step 4: Frontend Node Modules
if (Test-Path "frontend/node_modules") {
    $res = Report-Step 4 "Frontend Dependencies (node_modules)" $true "node_modules installed"
    $passedSteps++
} else {
    $res = Report-Step 4 "Frontend Dependencies (node_modules)" $false "frontend/node_modules not found. Run: npm install --prefix frontend"
}

# Step 5: Backend Pytest with Empty Key (Mock/Offline Safety)
try {
    $env:GEMINI_API_KEY = ""
    $pytestOutput = python -m pytest backend/tests/ -q 2>&1
    if ($LASTEXITCODE -eq 0) {
        $res = Report-Step 5 "Backend Pytest Suite (Offline/Zero-Key Mode)" $true "All backend tests passed ($pytestOutput)"
        $passedSteps++
    } else {
        $res = Report-Step 5 "Backend Pytest Suite (Offline/Zero-Key Mode)" $false "Tests failed. Output: $pytestOutput"
    }
} catch {
    $res = Report-Step 5 "Backend Pytest Suite (Offline/Zero-Key Mode)" $false $_.Exception.Message
}

# Step 6: Frontend TypeScript & Lint Check
try {
    $lintOutput = npm run lint --prefix frontend 2>&1
    if ($LASTEXITCODE -eq 0) {
        $res = Report-Step 6 "Frontend TypeScript Strict Check (npm run lint)" $true "0 TypeScript errors"
        $passedSteps++
    } else {
        $res = Report-Step 6 "Frontend TypeScript Strict Check (npm run lint)" $false "Lint errors detected"
    }
} catch {
    $res = Report-Step 6 "Frontend TypeScript Strict Check (npm run lint)" $false $_.Exception.Message
}

# Step 7: Frontend Production Build
try {
    $buildOutput = npm run build --prefix frontend 2>&1
    if ($LASTEXITCODE -eq 0) {
        $res = Report-Step 7 "Frontend Production Build (npm run build)" $true "Vite build successful"
        $passedSteps++
    } else {
        $res = Report-Step 7 "Frontend Production Build (npm run build)" $false "Vite build failed"
    }
} catch {
    $res = Report-Step 7 "Frontend Production Build (npm run build)" $false $_.Exception.Message
}

# Step 8: Docker Compose Configuration Check
try {
    $composeOutput = docker compose config --quiet 2>&1
    if ($LASTEXITCODE -eq 0) {
        $res = Report-Step 8 "Docker Compose Configuration" $true "docker-compose.yml is valid"
        $passedSteps++
    } else {
        $res = Report-Step 8 "Docker Compose Configuration" $false "docker compose config failed: $composeOutput"
    }
} catch {
    $res = Report-Step 8 "Docker Compose Configuration" $false "Docker command not available or daemon offline"
}

Write-Host "=================================================================" -ForegroundColor Cyan
if ($passedSteps -eq $totalSteps) {
    Write-Host "  RESULT: ALL $passedSteps/$totalSteps CHECKS PASSED (100% READY FOR IMPLEMENTATION)" -ForegroundColor Green
    Write-Host "  Paste this output into your Pull Request description as proof of setup." -ForegroundColor DarkGray
    exit 0
} else {
    Write-Host "  RESULT: $passedSteps/$totalSteps CHECKS PASSED. PLEASE FIX FAILED STEPS ABOVE." -ForegroundColor Red
    exit 1
}
