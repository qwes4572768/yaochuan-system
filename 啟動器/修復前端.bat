@echo off
chcp 65001 >nul
set "ROOT=%~dp0.."
cd /d "%ROOT%\frontend"

echo ========================================
echo   修復前端 (刪除 node_modules 後重裝)
echo ========================================
echo   若出現 rollup 或 Application Control 錯誤可試此檔
echo.

if not exist "package.json" (
    echo [錯誤] 找不到 frontend\package.json
    pause
    exit /b 1
)

echo 刪除 node_modules ...
if exist node_modules rd /s /q node_modules
echo 刪除 package-lock.json ...
if exist package-lock.json del /q package-lock.json
echo.
echo 重新安裝套件 (npm install) ...
call npm install
if errorlevel 1 (
    echo.
    echo [失敗] npm install 失敗。若仍被 Device Guard 阻擋，請將專案搬到 D:\ 或請 IT 放行路徑。
    pause
    exit /b 1
)
echo.
echo [完成] 請再執行「一鍵啟動（前後端）.bat」試試。
pause
