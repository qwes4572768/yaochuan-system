"""驗證 list_sites 分頁與 contract_active：呼叫 /api/sites 並檢查 total/items 與 contract_end。
執行前請：1) 後端已啟動  2) 已執行 python scripts/seed_sites_for_validation.py"""
import urllib.request
import urllib.parse
import json
import sys

BASE = "http://127.0.0.1:8000"


def get(path, query=None):
    url = BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def main():
    ok = True

    # 1) page=1, page_size=2, q=驗證 → total=3, items=2
    r = get("/api/sites", {"page": 1, "page_size": 2, "q": "驗證"})
    total, items = r.get("total"), r.get("items", [])
    if total != 3 or len(items) != 2:
        print("FAIL: page=1&page_size=2&q=驗證 期望 total=3 items=2，實際 total=%s len(items)=%s" % (total, len(items)))
        ok = False
    else:
        print("OK: page=1&page_size=2&q=驗證 → total=3, len(items)=2")

    # 2) page=2, page_size=2, q=驗證 → total=3, items=1
    r = get("/api/sites", {"page": 2, "page_size": 2, "q": "驗證"})
    total, items = r.get("total"), r.get("items", [])
    if total != 3 or len(items) != 1:
        print("FAIL: page=2&page_size=2&q=驗證 期望 total=3 items=1，實際 total=%s len(items)=%s" % (total, len(items)))
        ok = False
    else:
        print("OK: page=2&page_size=2&q=驗證 → total=3, len(items)=1")

    # 3) contract_active=false → 每筆 contract_end 皆非 null
    r = get("/api/sites", {"q": "驗證", "contract_active": "false"})
    items = r.get("items", [])
    for i, row in enumerate(items):
        ce = row.get("contract_end")
        if ce is None:
            print("FAIL: contract_active=false 回傳之第 %s 筆 contract_end 為 null" % (i + 1,))
            ok = False
            break
    else:
        print("OK: contract_active=false 回傳 %s 筆，皆符合 contract_end is not null" % (len(items),))

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
