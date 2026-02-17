import json
from datetime import date, datetime
from pathlib import Path
from typing import Set


_HOLIDAY_FILE = Path(__file__).resolve().parent / "data" / "tw_holidays_2025_2027.json"


def _load_holiday_map() -> dict[str, list[str]]:
    if not _HOLIDAY_FILE.exists():
        return {}
    try:
        return json.loads(_HOLIDAY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_holiday_dates(year: int, month: int) -> Set[date]:
    holidays: Set[date] = set()
    holiday_map = _load_holiday_map()
    for raw in holiday_map.get(str(year), []):
        try:
            d = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d.month == month:
            holidays.add(d)

    # 第一版：週六週日 + 國定假日（JSON）
    from calendar import monthrange

    _, last_day = monthrange(year, month)
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        if d.weekday() >= 5:
            holidays.add(d)
    return holidays
