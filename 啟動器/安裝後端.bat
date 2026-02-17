@echo off
chcp 65001 >nul
set "ROOT=%~dp0.."
cd /d "%ROOT%\backend"

echo === 後端依賴安裝 ===
if not exist .venv (
    echo 建立虛擬環境...
    python -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo 執行資料庫遷移...
.venv\Scripts\alembic.exe upgrade head
echo.
echo 後端安裝完成。
pause
