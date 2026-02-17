"""一鍵為 SQLite employees 表新增 pension_self_6 欄位（若尚無）。
執行方式（在 backend 目錄下）：
  python scripts/migrate_add_pension_self_6.py
或：
  py scripts/migrate_add_pension_self_6.py
"""
import sqlite3
import sys
from pathlib import Path

# 專案 backend 目錄
BACKEND_DIR = Path(__file__).resolve().parent.parent
# 預設 DB 路徑（與 config 一致）
DEFAULT_DB = BACKEND_DIR / "hr.db"


def main() -> int:
    db_path = DEFAULT_DB
    if not db_path.exists():
        print(f"找不到資料庫：{db_path}", file=sys.stderr)
        return 1
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
        if cur.fetchone() is None:
            print("employees 表不存在，略過。")
            conn.close()
            return 0
        cur.execute("PRAGMA table_info(employees)")
        existing = {row[1].lower() for row in cur.fetchall()}
        if "pension_self_6" in existing:
            print("employees.pension_self_6 已存在，無需變更。")
            conn.close()
            return 0
        cur.execute("ALTER TABLE employees ADD COLUMN pension_self_6 INTEGER NOT NULL DEFAULT 0")
        conn.commit()
        conn.close()
        print("已新增 employees.pension_self_6 欄位。")
        return 0
    except Exception as e:
        print(f"執行失敗：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
