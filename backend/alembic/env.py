"""Alembic 環境：使用 app 的 Base 與 database_url，支援 SQLite / PostgreSQL 遷移。
路徑一律用 pathlib 解析，避免 Windows 中文路徑與編碼問題。"""
from pathlib import Path
import sys

from logging.config import fileConfig

from alembic import context

# 專案根目錄（backend）加入 sys.path，不依賴 cwd，利於 Windows 中文路徑
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.config import settings
from app.database import Base
from app.models import Employee, Dependent, EmployeeDocument, InsuranceConfig

config = context.config
if config.config_file_name is not None:
    config_path = Path(config.config_file_name).resolve()
    if config_path.exists():
        fileConfig(str(config_path))

# 同步連線用 URL（Alembic 跑 sync）：asyncpg -> psycopg2、aiosqlite -> 無
# SQLite 相對路徑改為絕對路徑，避免 cwd 或中文路徑問題
target_metadata = Base.metadata
db_url = settings.database_url
if db_url.startswith("sqlite+aiosqlite"):
    sync_url = db_url.replace("sqlite+aiosqlite", "sqlite", 1)
    if sync_url.startswith("sqlite:///./"):
        rel = sync_url.replace("sqlite:///./", "").strip()
        abs_path = (_project_root / rel).resolve().as_posix()
        sync_url = "sqlite:///" + abs_path
elif db_url.startswith("sqlite:///"):
    sync_url = db_url
    if "./" in sync_url or "\\" in sync_url:
        parts = sync_url.replace("sqlite:///", "").strip()
        abs_path = (_project_root / parts).resolve().as_posix()
        sync_url = "sqlite:///" + abs_path
else:
    sync_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    """離線模式：只產生 SQL，不連 DB"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """線上模式：連 DB 執行遷移"""
    from sqlalchemy import create_engine
    url = config.get_main_option("sqlalchemy.url")
    connectable = create_engine(url)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
