@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 前端啟動中：http://localhost:5173
echo 關閉此視窗即停止前端。
echo.
call npm run dev
pause
