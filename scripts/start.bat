@echo off
chcp 65001 >nul
title SmartDesk AI - Development Server

echo ===================================================
echo           KHOI DONG SMARTDESK AI WEB APP
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Kiem tra Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Khong tim thay Node.js!
    echo Vui long cai dat Node.js tai https://nodejs.org/ truoc khi chay app.
    echo.
    pause
    exit /b 1
)

:: 2. Kiem tra va cai dat thu vien neu chua co node_modules
if not exist "node_modules\" (
    echo [THONG BAO] Phat hien chua cai dat node_modules.
    echo Dang tien hanh cai dat thu vien (npm install)...
    echo.
    call npm install
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Qua trinh cai dat thu vien that bai!
        pause
        exit /b %errorlevel%
    )
    echo.
    echo [SUCCESS] Cai dat thu vien thanh cong!
    echo.
)

:: 3. Chay web app va tu dong mo trinh duyet
echo [INFO] Dang khoi dong Web Server tai cong 3000...
echo Trinh duyet se tu dong mo http://localhost:3000
echo Nhan Ctrl+C de dung server bat cu luc nao.
echo ===================================================
echo.

call npm start

pause
