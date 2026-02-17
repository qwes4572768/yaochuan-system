@echo off
chcp 65001 >nul
set "BACKEND=%~dp0..\.."
cd /d "%BACKEND%"

echo ========================================
echo   後端：使用 Python 3.12 重建 venv 並啟動
echo ========================================

py -3.12 --version >nul 2>nul
if errorlevel 1 (
    echo [錯誤] 找不到 py -3.12，請安裝 Python 3.12 並勾選「Add to PATH」
    echo 下載：https://www.python.org/downloads/release/python-3120/
    echo 安裝後請刪除 backend\.venv 再執行本檔
    pause
    exit /b 1
)

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
    echo 建立 .venv (py -3.12) ...
    if exist "%BACKEND%\.venv" rd /s /q "%BACKEND%\.venv"
    py -3.12 -m venv "%BACKEND%\.venv"
    if errorlevel 1 (
        echo [錯誤] 建立 venv 失敗
        pause
        exit /b 1
    )
    echo 安裝依賴 requirements.txt（使用 .venv 的 Python）...
    "%BACKEND%\.venv\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements.txt"
    if errorlevel 1 (
        echo [錯誤] pip install 失敗
        pause
        exit /b 1
    )
    if not exist "%BACKEND%\.env" if exist "%BACKEND%\.env.example" copy "%BACKEND%\.env.example" "%BACKEND%\.env"
    echo 執行資料庫遷移...
    "%BACKEND%\.venv\Scripts\alembic.exe" -c "%BACKEND%\alembic.ini" upgrade head
) else (
    echo 使用既有 .venv (Python 3.12)
)
echo 修復 SQLite 缺欄（若為 SQLite）...
"%BACKEND%\.venv\Scripts\python.exe" "%BACKEND%\scripts\fix_sqlite_schema.py"
echo.
echo 啟動後端 API http://0.0.0.0:8000 ...
echo 關閉此視窗即停止後端。
echo.
"%BACKEND%\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
