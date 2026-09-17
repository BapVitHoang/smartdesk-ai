@echo off
chcp 65001 >nul
title SmartDesk AI - FastAPI Backend Server

echo ===================================================
echo       KHOI DONG SMARTDESK AI FASTAPI BACKEND
echo ===================================================
echo.

cd /d "%~dp0backend"

:: Kiem tra python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Khong tim thay Python!
    echo Vui long cai dat Python 3.11+ tai https://python.org
    pause
    exit /b 1
)

echo [INFO] Dang khoi dong Uvicorn ASGI Server tai cong 8000...
echo - API Docs (Swagger UI): http://localhost:8000/docs
echo - Health Probe:          http://localhost:8000/api/v1/health
echo - Nhan Ctrl+C de dung server bat cu luc nao.
echo ===================================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
