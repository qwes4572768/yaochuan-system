# list_sites 分頁與 contract_active 驗證

**狀態：已完成並通過驗證。** 此段邏輯（total/items SQL、分頁、q、contract_active）請勿修改；後續僅在使用者提出新需求時再變更。

---

## 1) 確認 total / items SQL（可選）

在 `app/crud.py` 的 `list_sites` 中暫時加上：

```python
# 在 total = await db.scalar(total_stmt) 前
print("[list_sites] total_stmt SQL:", str(total_stmt.compile()))
# 在 r = await db.execute(items_stmt) 前
print("[list_sites] items_stmt SQL:", str(items_stmt.compile()))
```

啟動後端後呼叫：

```
GET /api/sites?page=1&page_size=2&q=驗證
```

確認：total_stmt SQL **不**含 `ORDER BY`、`LIMIT`、`OFFSET`；items_stmt SQL **含** `ORDER BY`、`LIMIT`、`OFFSET`。驗證完請刪除上述兩行 print。

---

## 2) 最小可重現資料與 API 驗證

1. 後端已啟動、已執行過 `alembic upgrade head`。
2. 種子 3 筆案場（名稱皆含「驗證」）：

   ```bash
   cd backend
   .venv\Scripts\activate
   python scripts/seed_sites_for_validation.py
   ```

3. 呼叫 API 驗證分頁：
   - `GET /api/sites?page=1&page_size=2&q=驗證` → 回傳 `total=3`、`items` 長度 2。
   - `GET /api/sites?page=2&page_size=2&q=驗證` → 回傳 `total=3`、`items` 長度 1。

4. 或直接跑驗證腳本（後端須已啟動）：

   ```bash
   python scripts/verify_sites_api.py
   ```

   通過則印出三行 OK 並 exit 0。

---

## 3) contract_active=false

呼叫：

```
GET /api/sites?q=驗證&contract_active=false
```

確認回傳的每一筆 `contract_end` 皆非 null（種子資料之 3 筆案場 contract_end 皆為 2020-01-01，符合已結束合約）。驗證腳本會一併檢查。
