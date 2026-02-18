"""啟動時偵測 SQLite sites 表缺欄則補、缺表則建（不刪資料）。
與 009 migration 邏輯一致，確保未跑 migration 時 /api/sites 也能正常。"""
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from app.config import settings, BASE_DIR

logger = logging.getLogger(__name__)

# 各表可能缺少的欄位（與 SQLAlchemy Model 一致）：(欄位名, SQLite 型別)
# SQLite 無 BOOLEAN，用 INTEGER(0/1) 與 REAL
SQLITE_ADD_COLUMNS: dict[str, List[Tuple[str, str]]] = {
    "employees": [
        ("pension_self_6", "INTEGER NOT NULL DEFAULT 0"),
        ("registration_type", "VARCHAR(20) NOT NULL DEFAULT 'security'"),
        ("pay_method", "VARCHAR(20) NOT NULL DEFAULT 'CASH'"),
        ("bank_code", "TEXT"),
        ("branch_code", "TEXT"),
        ("bank_account", "TEXT"),
        # 各公司別計薪模式（本次需求）
        ("property_pay_mode", "TEXT"),
        ("security_pay_mode", "TEXT"),
        ("smith_pay_mode", "TEXT"),
        ("lixiang_pay_mode", "TEXT"),
        # 現行物業計算會用到，舊 DB 若缺欄會在查詢時 500
        ("property_salary", "REAL"),
        ("weekly_amount", "REAL"),
    ],
    "site_monthly_receipts": [("proof_pdf_path", "TEXT")],
    "site_rebates": [("receipt_pdf_path", "TEXT")],
    "salary_profiles": [
        ("group_insurance_enabled", "INTEGER NOT NULL DEFAULT 0"),
        ("group_insurance_fee", "REAL NOT NULL DEFAULT 0"),
        ("self_pension_6_enabled", "INTEGER NOT NULL DEFAULT 0"),
        ("self_pension_rate", "REAL NOT NULL DEFAULT 0.06"),
    ],
    "accounting_payroll_results": [
        ("pay_type", "TEXT"),
        ("gross_salary", "REAL"),
        ("labor_insurance_employee", "REAL"),
        ("health_insurance_employee", "REAL"),
        ("group_insurance", "REAL"),
        ("self_pension_6", "REAL"),
        ("deductions_total", "REAL"),
        ("net_salary", "REAL"),
        ("created_at", "DATETIME"),
    ],
    "patrol_points": [
        ("public_id", "TEXT"),
        ("location", "TEXT"),
        ("is_active", "INTEGER NOT NULL DEFAULT 1"),
    ],
    "patrol_logs": [
        ("employee_id", "INTEGER"),
    ],
    "patrol_devices": [
        ("password_hash", "TEXT"),
        ("is_active", "INTEGER NOT NULL DEFAULT 1"),
        ("unbound_at", "DATETIME"),
    ],
}

SITES_ADD_COLUMNS: List[Tuple[str, str, Optional[str]]] = [
    ("site_type", "TEXT", None),
    ("service_types", "TEXT", None),
    ("monthly_fee_excl_tax", "NUMERIC(12,2)", None),
    ("tax_rate", "NUMERIC(5,4)", "0.05"),
    ("monthly_fee_incl_tax", "NUMERIC(12,2)", None),
    ("invoice_due_day", "INTEGER", None),
    ("payment_due_day", "INTEGER", None),
    ("remind_days", "INTEGER", "30"),
    ("customer_name", "TEXT", None),
    ("customer_tax_id", "TEXT", None),
    ("customer_contact", "TEXT", None),
    ("customer_phone", "TEXT", None),
    ("customer_email", "TEXT", None),
    ("invoice_title", "TEXT", None),
    ("invoice_mail_address", "TEXT", None),
    ("invoice_receiver", "TEXT", None),
    ("is_active", "BOOLEAN", "1"),
    ("deactivated_at", "DATETIME", None),
    ("deactivated_reason", "VARCHAR(50)", None),
    ("is_archived", "BOOLEAN", "0"),
    ("archived_at", "DATETIME", None),
    ("archived_reason", "VARCHAR(50)", None),
]


def fix_sqlite_missing_columns(db_path: Path) -> bool:
    """檢查並補齊 SQLite 各表缺欄（不刪資料）。回傳是否成功。"""
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        for table, columns in SQLITE_ADD_COLUMNS.items():
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cur.fetchone() is None:
                continue
            cur.execute(f"PRAGMA table_info({table})")
            existing = {row[1].lower() for row in cur.fetchall()}
            for col_name, col_type in columns:
                if col_name.lower() in existing:
                    continue
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                logger.info("%s: added column %s", table, col_name)
            if table == "patrol_points":
                # 既有資料補上永久 public_id，避免 QR 失效
                cur.execute("SELECT id, public_id FROM patrol_points")
                for row_id, public_id in cur.fetchall():
                    if public_id:
                        continue
                    cur.execute(
                        "UPDATE patrol_points SET public_id=? WHERE id=?",
                        (str(uuid.uuid4()), row_id),
                    )
                cur.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_patrol_points_public_id ON patrol_points (public_id)"
                )
        conn.commit()
        return True
    except Exception as e:
        logger.warning("fix_sqlite_missing_columns: %s", e)
        return False
    finally:
        if conn is not None:
            conn.close()


def _get_sqlite_path() -> Optional[Path]:
    url = getattr(settings, "database_url", "") or ""
    if "sqlite" not in url:
        return None
    raw = url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "").strip()
    if raw.startswith("./"):
        return (BASE_DIR / raw[2:].lstrip("/")).resolve()
    if raw.startswith(".\\"):
        return (BASE_DIR / raw[2:].lstrip("\\")).resolve()
    return Path(raw).resolve()


def ensure_sites_schema() -> None:
    """若為 SQLite，先補齊各表缺欄（如 employees.pension_self_6），再檢查 sites 表缺欄則 ADD COLUMN、三張表不存在則 CREATE TABLE。可重複執行。"""
    path = _get_sqlite_path()
    if not path or not path.exists():
        return
    try:
        import sqlite3
    except ImportError:
        return
    # 先補齊 employees 等表缺欄，避免 500（不依賴 sites 是否存在）
    fix_sqlite_missing_columns(path)
    try:
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        # 檢查 sites 是否存在
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sites'")
        if cur.fetchone() is None:
            conn.close()
            return
        cur.execute("PRAGMA table_info(sites)")
        existing = {row[1].lower() for row in cur.fetchall()}
        for col_name, col_type, default in SITES_ADD_COLUMNS:
            if col_name.lower() in existing:
                continue
            default_clause = f" DEFAULT {default}" if default is not None else ""
            cur.execute(f"ALTER TABLE sites ADD COLUMN {col_name} {col_type}{default_clause}")
            logger.info("sites: added column %s", col_name)
        # 三張表若不存在則建立
        for create_sql in [
            """CREATE TABLE IF NOT EXISTS site_contract_files (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                uploaded_at DATETIME
            )""",
            """CREATE TABLE IF NOT EXISTS site_rebates (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
                item_name VARCHAR(200) NOT NULL,
                is_completed BOOLEAN DEFAULT 0,
                completed_date DATE,
                cost_amount NUMERIC(12,2),
                receipt_pdf_path VARCHAR(500),
                notes TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )""",
            """CREATE TABLE IF NOT EXISTS site_monthly_receipts (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
                billing_month VARCHAR(7) NOT NULL,
                expected_amount NUMERIC(12,2),
                is_received BOOLEAN DEFAULT 0,
                received_date DATE,
                received_amount NUMERIC(12,2),
                payment_method VARCHAR(20),
                proof_pdf_path VARCHAR(500),
                notes TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                UNIQUE (site_id, billing_month)
            )""",
        ]:
            cur.execute(create_sql)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_site_contract_files_site_id ON site_contract_files (site_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_site_rebates_site_id ON site_rebates (site_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_site_monthly_receipts_site_id ON site_monthly_receipts (site_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_site_monthly_receipts_billing_month ON site_monthly_receipts (billing_month)")
        conn.commit()
        conn.close()
        # 新建的 site 相關表可能尚缺欄位，再補一次
        fix_sqlite_missing_columns(path)
    except Exception as e:
        logger.warning("db_schema_fix ensure_sites_schema: %s", e)
        try:
            conn.close()
        except Exception:
            pass


def _ensure_sqlite_columns_only(path: Path) -> None:
    """僅執行補缺欄（不建表）。供 startup 在 ensure_sites_schema 之後呼叫。"""
    fix_sqlite_missing_columns(path)


def ensure_schema() -> None:
    """
    App 啟動時執行的 SQLite schema 安全補齊：
    - 先補既有資料表缺欄（包含 employees 各公司別 pay_mode）
    - 再補 sites 相關擴充欄位/表
    """
    ensure_sites_schema()
