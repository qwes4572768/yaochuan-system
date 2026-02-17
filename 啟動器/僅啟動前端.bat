@echo off
chcp 65001 >nul
set "ROOT=%~dp0.."
cd /d "%ROOT%\frontend"

if not exist "node_modules" (
    echo [錯誤] 前端尚未安裝，請先執行「安裝前端.bat」
    pause
    exit /b 1
)

echo 前端啟動中：http://localhost:5173
echo 關閉此視窗即停止前端。
echo.
set ROLLUP_SKIP_NATIVE=1
call npm run dev
pause
