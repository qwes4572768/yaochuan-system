@echo off
chcp 65001 >nul
set "FRONTEND=%~dp0..\.."
cd /d "%FRONTEND%"

echo ========================================
echo   前端修復：刪除依賴後重裝並啟動
echo ========================================

for /f "tokens=*" %%v in ('node -v 2^>nul') do set NODEVER=%%v
echo 目前 Node 版本: %NODEVER%

echo 刪除 node_modules ...
if exist node_modules rd /s /q node_modules
echo 刪除 package-lock.json ...
if exist package-lock.json del /q package-lock.json
echo npm cache clean --force ...
call npm cache clean --force
echo npm install ...
call npm install
if errorlevel 1 (
    echo [錯誤] npm install 失敗，請確認網路與 Node 20 或 22 LTS
    pause
    exit /b 1
)
echo.
echo 啟動前端，使用 ROLLUP_SKIP_NATIVE 避開原生模組 ...
set ROLLUP_SKIP_NATIVE=1
call npm run dev
pause
