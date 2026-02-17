"""案場相關檔案儲存：回饋依據 PDF、每月匯款證明 PDF。路徑存於 uploads/sites/{site_id}/...，DB 只存相對路徑。"""
from pathlib import Path

from app import config as app_config

# 相對路徑用的子目錄名稱
REBATE_RECEIPT_FILENAME = "receipt.pdf"
MONTHLY_PROOF_FILENAME = "proof.pdf"


def get_upload_base() -> Path:
    """取得 upload 根目錄（絕對路徑）。"""
    base = app_config.settings.upload_dir
    if not base.is_absolute():
        base = app_config.BASE_DIR / base
    return base


def save_site_pdf(
    site_id: int,
    record_type: str,
    record_id: int,
    content: bytes,
    filename: str,
) -> str:
    """
    將 PDF 寫入 uploads/sites/{site_id}/{record_type}/{record_id}/{filename}。
    record_type 為 'rebates' 或 'monthly_receipts'。
    回傳相對於 upload 根目錄的路徑字串（供 DB 儲存），例如 sites/5/rebates/3/receipt.pdf。
    """
    base = get_upload_base()
    rel_dir = Path("sites") / str(site_id) / record_type / str(record_id)
    dest_dir = base / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    # 統一副檔名為 .pdf
    safe_name = Path(filename).name
    if not safe_name.lower().endswith(".pdf"):
        safe_name = (Path(filename).stem or "file") + ".pdf"
    dest_path = dest_dir / safe_name
    dest_path.write_bytes(content)
    return str(rel_dir / safe_name)


def resolve_site_file_path(relative_path: str) -> Path:
    """由 DB 存的相對路徑還原成絕對路徑。"""
    if not relative_path:
        raise ValueError("relative_path is empty")
    base = get_upload_base()
    return base / relative_path
