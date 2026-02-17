@echo off
chcp 65001 >nul
set "ROOT=%~dp0.."
cd /d "%ROOT%\backend"

if not exist ".venv\Scripts\python.exe" (
    echo [錯誤] 後端尚未安裝，請先執行「安裝後端.bat」
    pause
    exit /b 1
)

echo 後端啟動中：http://localhost:8000
echo API 文件：http://localhost:8000/docs
echo 關閉此視窗即停止後端。
echo.
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
