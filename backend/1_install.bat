@echo off
chcp 65001 >nul
echo === 後端依賴安裝 ===
cd /d "%~dp0"
if not exist .venv (
    echo 建立虛擬環境...
    python -m venv .venv
)
echo 安裝 Python 套件（使用 .venv 的 Python）...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo 執行資料庫遷移...
.venv\Scripts\python.exe -m alembic upgrade head
echo.
echo 後端依賴安裝完成。
pause
