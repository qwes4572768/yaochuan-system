@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [錯誤] 找不到後端環境，請先執行：1_install.bat
    echo 安裝完成後再執行本檔。
    pause
    exit /b 1
)

echo 修復 SQLite 缺欄（若為 SQLite）...
.venv\Scripts\python.exe scripts\fix_sqlite_schema.py
echo.
echo 後端啟動中：http://localhost:8000
echo API 文件：http://localhost:8000/docs
echo 關閉此視窗即停止後端。
echo.
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
