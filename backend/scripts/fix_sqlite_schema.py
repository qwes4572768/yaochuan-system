"""
SQLite 修復腳本：補齊 Model 有但 DB 缺少的欄位（不刪資料）。
可手動執行：在 backend 目錄下執行 python scripts/fix_sqlite_schema.py
或由後端 startup / 啟動 bat 自動呼叫。
"""
import sys
from pathlib import Path

# 確保可 import app（從 backend 執行時）
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _get_sqlite_path():
    """從 env 取得 SQLite DB 路徑（與 app.db_schema_fix 一致）。"""
    try:
        from app.db_schema_fix import _get_sqlite_path as get_path
        return get_path()
    except Exception:
        pass
    try:
        from app.config import settings, BASE_DIR
        url = getattr(settings, "database_url", "") or ""
        if "sqlite" not in url:
            return None
        raw = url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "").strip()
        if raw.startswith("./"):
            path = (BASE_DIR / raw[2:].lstrip("/")).resolve()
        elif raw.startswith(".\\"):
            path = (BASE_DIR / raw[2:].lstrip("\\")).resolve()
        else:
            path = Path(raw).resolve()
        return path if path.exists() else None
    except Exception:
        return None


def _find_db_path():
    """取得 SQLite 路徑：先從 env，再試常見路徑。"""
    path = _get_sqlite_path()
    if path and path.exists():
        return path
    try:
        from app.config import BASE_DIR
    except Exception:
        BASE_DIR = BACKEND_DIR
    for candidate in [
        BASE_DIR / "hr.db",
        BASE_DIR / "app.db",
        BASE_DIR / "data" / "app.db",
    ]:
        if candidate.exists():
            return candidate
    return None


def main():
    db_path = _find_db_path()
    if not db_path:
        print("找不到 SQLite 資料庫。請確認：")
        print("  1) .env 中 database_url 為 sqlite（例如 sqlite+aiosqlite:///./hr.db）")
        print("  2) 或於 backend 目錄下存在 hr.db / app.db / data/app.db")
        sys.exit(1)
    print(f"使用資料庫：{db_path}")
    from app.db_schema_fix import ensure_schema, fix_sqlite_missing_columns
    # 先跑整體 ensure（含 sites 擴充補齊），再補一次缺欄以確保舊 DB 都被修復
    ensure_schema()
    if not fix_sqlite_missing_columns(db_path):
        sys.exit(2)
    print("修復完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
