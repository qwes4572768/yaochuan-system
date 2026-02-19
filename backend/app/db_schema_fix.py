"""
SQLite schema fix (safe)
- main.py 會 import ensure_schema，所以一定要存在
- 只在 SQLite 連線下才會嘗試補欄位；PostgreSQL 一律不做事
"""

import logging
import sqlite3
from app.config import settings

logger = logging.getLogger(__name__)


def ensure_schema():
    """
    舊版專案會在啟動時呼叫 ensure_schema() 來補 SQLite 欄位。
    為了避免正式 PostgreSQL 被誤改，這裡只在 SQLite 才執行。
    """
    db_url = str(getattr(settings, "database_url", "") or "").lower()
    if not db_url.startswith("sqlite"):
        # ✅ PostgreSQL / 其他資料庫：不做任何事
        return

    # ✅ SQLite：嘗試做「非破壞性」補欄位（可依需要擴充）
    try:
        # 支援 sqlite:///xxx.db 或 sqlite:////abs/path.db
        path = db_url.split("sqlite:///", 1)[-1] if "sqlite:///" in db_url else None
        if not path or path.startswith(":memory:"):
            return

        conn = sqlite3.connect(path)
        cur = conn.cursor()

        # 這裡先放一個「安全範本」：沒有要補什麼也不會壞
        # 你以後若要補欄位，可以照這個模式加：
        # - 先查 PRAGMA table_info
        # - 再 ALTER TABLE ADD COLUMN

        conn.commit()
        conn.close()

    except Exception:
        logger.exception("ensure_schema() failed on sqlite; ignored")
        # 不要讓啟動失敗
        return
