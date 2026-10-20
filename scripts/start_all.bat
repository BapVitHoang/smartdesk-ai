@echo off
chcp 65001 >nul
title SmartDesk AI - Khoi dong toan bo he thong

echo ===================================================
echo     KHOI DONG SMARTDESK AI (FRONTEND + BACKEND)
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Khoi dong Backend trong cua so rieng
echo [1/2] Dang khoi dong Backend FastAPI tai http://localhost:8000...
start "SmartDesk AI - Backend" cmd /c "start_backend.bat"

:: 2. Doi 2 giay de Backend on dinh
timeout /t 2 /nobreak >nul

:: 3. Khoi dong Frontend tai port 3000
echo [2/2] Dang khoi dong Frontend tai http://localhost:3000...
call npm start
