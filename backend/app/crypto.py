"""敏感欄位加密/解密與遮罩 - 身分證、地址、銀行帳號"""
from typing import Optional

from cryptography.fernet import Fernet
from app.config import settings

_fernet_instance: Optional[Fernet] = None


def _fernet() -> Optional[Fernet]:
    """ENCRYPTION_KEY 須為 Fernet 金鑰（32 bytes base64，約 44 字元），可由 Fernet.generate_key() 產生"""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    key = settings.encryption_key
    if not key or len(key) < 44:
        return None
    try:
        _fernet_instance = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
        return _fernet_instance
    except Exception:
        return None


def encrypt(plain: Optional[str]) -> Optional[str]:
    """加密字串，若未設定 key 或為空則回傳原值"""
    if not plain:
        return plain
    f = _fernet()
    if not f:
        return plain
    try:
        return f.encrypt(plain.encode("utf-8")).decode("utf-8")
    except Exception:
        return plain


def decrypt(cipher: Optional[str]) -> Optional[str]:
    """解密；若未加密或無 key 則回傳原值。若解密失敗（非加密內容）則回傳原值"""
    if not cipher:
        return cipher
    f = _fernet()
    if not f:
        return cipher
    try:
        return f.decrypt(cipher.encode("utf-8")).decode("utf-8")
    except Exception:
        return cipher


def mask_id_number(value: Optional[str]) -> str:
    """身分證遮罩：前 2 後 4，中間 ***（後 4 供列表搜尋用）"""
    if not value or len(value) < 4:
        return "***"
    return value[:2] + "****" + value[-4:]


def mask_address(value: Optional[str]) -> str:
    """地址遮罩：前 6 字 + ***"""
    if not value or len(value) <= 6:
        return "***"
    return value[:6] + "***"


def mask_bank_account(value: Optional[str]) -> str:
    """銀行帳號遮罩：僅顯示後 4 碼"""
    if not value or len(value) < 4:
        return "****"
    return "****" + value[-4:]
