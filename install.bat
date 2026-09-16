@echo off
chcp 65001 >nul
title SmartDesk AI - Cai dat thu vien

echo ===================================================
echo        CAI DAT THU VIEN CHO SMARTDESK AI
echo ===================================================
echo.

cd /d "%~dp0"

echo Dang chay npm install...
echo.
call npm install

if %errorlevel% equ 0 (
    echo.
    echo ===================================================
    echo [SUCCESS] Cai dat thu vien hoan tat thanh cong!
    echo Ban co the chay file start.bat hoac go "npm start".
    echo ===================================================
) else (
    echo.
    echo ===================================================
    echo [ERROR] Co loi xay ra trong qua trinh cai dat!
    echo ===================================================
)

echo.
pause
