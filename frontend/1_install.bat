@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo === 前端依賴安裝 ===
echo.

REM 檢查是否有 npm（Node.js 會一併安裝 npm）
where npm >nul 2>nul
if errorlevel 1 (
    echo [錯誤] 找不到 npm，請先安裝 Node.js。
    echo.
    echo Node.js 內含 npm，請到官網下載 LTS 版本：
    echo   https://nodejs.org
    echo.
    echo 安裝完成後「關閉並重新開啟」命令提示字元或 Cursor，
    echo 再執行本批次檔。
    echo.
    start https://nodejs.org
    echo 已嘗試開啟 Node.js 官網，請下載並安裝。
    pause
    exit /b 1
)

echo 安裝 npm 套件...
call npm install
echo.
echo 前端依賴安裝完成。
pause
