@echo off
chcp 65001 >nul
set "ROOT=%~dp0.."
cd /d "%ROOT%"

if not exist "%ROOT%\backend" (
    echo [錯誤] 找不到 backend 資料夾
    goto :fail
)
if not exist "%ROOT%\frontend" (
    echo [錯誤] 找不到 frontend 資料夾
    goto :fail
)

echo ========================================
echo   保全公司管理系統 - 前後端一鍵一起開
echo ========================================
echo.

REM ---------- 1. 後端：呼叫 recreate_venv_py312.bat 在新視窗啟動 ----------
echo [1/2] 後端：呼叫 backend\scripts\windows\recreate_venv_py312.bat 並啟動...
if not exist "%ROOT%\backend\scripts\windows\recreate_venv_py312.bat" (
    echo [錯誤] 找不到 backend\scripts\windows\recreate_venv_py312.bat
    goto :fail
)
start "Backend-8000" cmd /k "cd /d ""%ROOT%\backend"" && scripts\windows\recreate_venv_py312.bat"
cd /d "%ROOT%"

echo 請勿關閉「Backend-8000」視窗，後端需持續運行。
echo 等待後端就緒，最多 60 秒...
set /a count=0
:wait_backend
timeout /t 3 /nobreak >nul
powershell -NoProfile -Command "$t=New-Object System.Net.Sockets.TcpClient;try{$t.Connect('127.0.0.1',8000);$t.Close();exit 0}catch{exit 1}" >nul 2>nul
if not errorlevel 1 goto :backend_ready
set /a count+=3
if %count% geq 60 (
    echo [警告] 後端 60 秒內未就緒，請檢查 Backend-8000 視窗是否有錯誤。
    echo 若後端正常啟動，請手動重新整理網頁。現在仍會啟動前端...
    goto :backend_ready
)
echo 尚在等待後端，已等 %count% 秒...
goto :wait_backend
:backend_ready
echo Backend ready.
echo.

REM ---------- 2. 前端（檢查 Node 非 24） ----------
echo [2/2] 前端 (http://localhost:5173) ...
for /f "tokens=*" %%v in ('node -v 2^>nul') do set NODEVER=%%v
echo %NODEVER% | findstr /r "v24\." >nul 2>nul
if not errorlevel 1 (
    echo [錯誤] 目前為 Node 24，請改用 Node 20 或 22 LTS 後再執行本檔。
    echo 請至 nodejs.org 下載 LTS 版本。
    goto :fail
)
if not exist "%ROOT%\frontend\node_modules" (
    echo 尚未安裝，正在 npm install ...
    cd /d "%ROOT%\frontend"
    call npm install
    if errorlevel 1 (
        echo [前端失敗] 請改裝 Node 20 或 22 LTS 後執行 frontend\scripts\windows\reinstall_frontend.bat
        goto :fail
    )
    cd /d "%ROOT%"
)

start http://localhost:5173
cd /d "%ROOT%\frontend"
set ROLLUP_SKIP_NATIVE=1
call npm run dev
if errorlevel 1 (
    echo.
    echo [前端失敗] 若出現 rollup 或 Application Control 錯誤：
    echo   [1] 請安裝 Node 20 或 22 LTS ^(nodejs.org^)
    echo   [2] 執行 frontend\scripts\windows\reinstall_frontend.bat 重裝前端
    echo   [3] 若仍被阻擋，請將專案移到英文路徑後再重裝 node_modules
    goto :fail
)

echo.
echo 前端已結束。
goto :end

:fail
echo.
echo ----------------------------------------
echo 修復方式：
echo   前端顯示「伺服器發生錯誤」/ ECONNREFUSED 8000：表示後端未啟動
echo     → 請先單獨執行「僅啟動後端.bat」，確認視窗無錯誤且顯示 Uvicorn 運行後，再執行本檔
echo   後端錯誤：執行 backend\scripts\windows\recreate_venv_py312.bat 用 Python 3.12 重建
echo   前端 Node 24 或 rollup 錯誤：安裝 Node 20 或 22 LTS，再執行 frontend\scripts\windows\reinstall_frontend.bat
echo   Application Control 阻擋時：請將專案移到英文路徑再重裝 node_modules
echo ----------------------------------------
:end
pause
