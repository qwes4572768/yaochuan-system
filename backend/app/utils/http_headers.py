"""
HTTP header 工具：RFC 5987 Content-Disposition 支援中文檔名。
Starlette/FastAPI 的 header 僅支援 latin-1，不可直接塞中文；
使用 filename (ASCII fallback) + filename*=UTF-8''... 可讓瀏覽器正確顯示中文檔名。
"""
from urllib.parse import quote


def build_content_disposition(ascii_filename: str, unicode_filename: str) -> str:
    """
    組出 RFC 5987 的 Content-Disposition 字串，供 Response headers 使用。

    - filename：ASCII 檔名（fallback），避免 latin-1 編碼錯誤。
    - filename*：UTF-8 檔名（urlencode），瀏覽器會優先使用此顯示。

    範例：
        build_content_disposition(
            "security_payroll_2026_01.xlsx",
            "保全核薪_2026_01.xlsx"
        )
    """
    # 雙引號內若有 \ 或 " 需跳脫，此處檔名通常不含，直接包雙引號
    ascii_part = f'attachment; filename="{ascii_filename}"'
    # RFC 5987: filename*=UTF-8''%encoded
    encoded = quote(unicode_filename, safe="")
    return f"{ascii_part}; filename*=UTF-8''{encoded}"
