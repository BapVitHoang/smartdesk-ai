@echo off
chcp 65001 >nul
title SmartDesk AI - Cai dat thu vien toan bo du an

echo ===================================================
echo        CAI DAT THU VIEN CHO SMARTDESK AI
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Cai dat Frontend (Node.js)
echo [1/2] Dang cai dat thu vien Frontend (npm install)...
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Cai dat Frontend that bai!
    pause
    exit /b %errorlevel%
)
echo [SUCCESS] Cai dat Frontend hoan tat!
echo.

:: 2. Cai dat Backend (Python)
echo [2/2] Dang cai dat thu vien Python Backend (pip install)...
where python >nul 2>nul
if %errorlevel% equ 0 (
    python -m pip install -r backend/requirements.txt
    if %errorlevel% equ 0 (
        echo [SUCCESS] Cai dat Backend Python hoan tat!
    ) else (
        echo [WARNING] Co canh bao khi cai dat thu vien Python.
    )
) else (
    echo [WARNING] Khong tim thay Python. Vui long cai dat Python 3.11+ de chay backend.
)

echo.
echo ===================================================
echo [SUCCESS] Hoan tat cai dat! Chay start_all.bat de khoi dong ca he thong.
echo ===================================================
echo.
pause
