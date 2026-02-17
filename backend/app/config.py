"""應用設定與環境變數"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

# 後端專案根目錄（backend/），相對路徑以此為基準，不受工作目錄影響
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "保全公司管理系統 - HR"
    debug: bool = True
    # SQLite 範例：sqlite+aiosqlite:///./hr.db
    # PostgreSQL 範例：postgresql+asyncpg://user:pass@localhost:5432/hr
    database_url: str = "sqlite+aiosqlite:///./hr.db"
    upload_dir: Path = Path("./uploads")
    max_upload_size_mb: int = 10
    # 敏感欄位加密用（32 bytes base64），若未設則不加密僅遮罩
    encryption_key: Optional[str] = None
    # 人事備份/還原僅管理員可用：設此值後，請求須帶 X-Admin-Token 與此相同
    admin_backup_token: Optional[str] = None
    # 自動備份：存放目錄（相對專案根或絕對路徑）、保留份數、每日執行時間（HH:MM）
    backup_dir: Path = Path("server/backup/hr")
    backup_retention_count: int = 30
    backup_schedule_time: str = "00:00"
    # 團保固定月費（不從 Excel 級距表讀取，系統固定參數；全由員工負擔）
    group_insurance_monthly_fee: int = 350
    # 巡邏綁定 QR 對外公開網址（手機可連線）；未設時 fallback 本機
    public_base_url: str = "http://127.0.0.1:8000"

    class Config:
        env_file = str(BASE_DIR / ".env")


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
