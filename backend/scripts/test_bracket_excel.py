"""實測級距表 Excel：讀取指定檔案並解析，印出級距 42000 那一列。"""
import asyncio
import sys
from pathlib import Path

# 專案根目錄
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# 桌面上的 Excel（可改路徑）
EXCEL_PATH = Path(r"c:\Users\USER\Desktop\115(2026年)勞保健保勞退級距表格（點選「檔案」⭢「下載」⭢「選擇需要的檔案類型」後使用）.xlsx")


def main():
    if not EXCEL_PATH.is_file():
        print(f"檔案不存在: {EXCEL_PATH}")
        return
    content = EXCEL_PATH.read_bytes()
    from app.services.bracket_excel_parser import parse_bracket_excel

    result = parse_bracket_excel(content)
    rows = result.get("rows") or []
    errors = result.get("errors") or []
    print(f"解析到 {len(rows)} 筆級距")
    if errors:
        print("errors:", errors[:5])
    row_42000 = next((r for r in rows if r["insured_salary_level"] == 42000), None)
    if row_42000:
        print("級距 42000 一列:", row_42000)
        print("預期: 勞保雇主 3675, 健保雇主 2032, 職災 88.2, 勞退 2520, 勞保員工 1050, 健保員工 651")
    else:
        print("未找到級距 42000，前幾筆 level:", [r["insured_salary_level"] for r in rows[:15]])


if __name__ == "__main__":
    main()
