@echo off
chcp 65001 >nul
set "ROOT=%~dp0.."
cd /d "%ROOT%\frontend"

echo === 前端依賴安裝 ===
where npm >nul 2>nul
if errorlevel 1 (
    echo [錯誤] 找不到 npm，請先安裝 Node.js。
    echo 請至 nodejs.org 下載 LTS 版本。
    start https://nodejs.org
    pause
    exit /b 1
)
echo 安裝 npm 套件...
call npm install
echo.
echo 前端安裝完成。
pause
