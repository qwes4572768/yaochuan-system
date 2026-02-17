# 保全核薪：Excel 匯出與年月驗證方式

## 一鍵清除指定年月（安全刪除）

**API**：`POST /api/accounting/security-payroll/delete`  
**Body**：`{ "year": 2026, "month": 2, "payroll_type": "security" }`

- 同一 transaction：先 `COUNT(*)` 再 `DELETE`，條件僅限 `year` / `month` / `type`，不 drop table、不刪其他月份。
- 回傳：`{ "deleted_count": X, "count_before": N, "year": y, "month": m, "type": "security" }`（type 一律為英文 'security'，不可用中文）。

---

## 驗證流程（四步）

1. **history 有筆數**：`GET .../history?year=2026&month=2&payroll_type=security` → 目前筆數 > 0。
2. **delete 成功**：`POST .../delete` body `{ "year": 2026, "month": 2, "payroll_type": "security" }` → `deleted_count` > 0。
3. **history 變 0 筆**：再呼叫 `GET .../history?year=2026&month=2&payroll_type=security` → 必須回傳 0 筆。
4. **覆蓋不累加**：再次對同年月 upload 計算 → 再查 history，筆數不會累加，只會是該批筆數（upload 回傳有 `deleted_before_insert`、`inserted` 可對照）。

---

## 1) 同年月上傳兩次：覆蓋、不亂跳、不倍增

**操作**：選擇 **2026/01**，上傳時數檔並按「計算」→ 再選同一檔案再按「計算」一次。

**預期**：

- DB 只會有 **2026/01** 的資料，不會出現 2026/02。
- 筆數不會倍增（第二次會先刪除該月份該類別舊資料，再寫入新資料，等同覆蓋）。

**實作**：`POST /api/accounting/security-payroll/upload` 內同一 transaction 先 `delete_payroll_results_for_period(db, y, m, payroll_type)` 再 `save_payroll_results(...)`，year/month 一律來自 request 的 form（絕不使用 `datetime.now()` 推導存檔年月）。回傳含 `deleted_before_insert`、`inserted` 供驗證「先刪再寫入」。

---

## 2) 匯出 Excel：GET 成功、檔名中文

**操作**：

- **GET**：`GET /api/accounting/security-payroll/export?year=2026&month=1`（或從前端「歷史查詢」選 2026 年 1 月後按「匯出歷史 Excel」）。
- 預期：成功下載，檔名顯示為 **保全核薪_2026_01.xlsx**（或至少瀏覽器下載名稱正確、不因 latin-1 報 500）。

**實作**：匯出使用 `StreamingResponse` + `build_content_disposition(ascii_filename, unicode_filename)`（RFC 5987：`filename` ASCII fallback + `filename*=UTF-8''` 中文），避免 `Content-Disposition` 直接塞中文造成 `UnicodeEncodeError`。

---

## 3) 未帶 year/month 上傳：400 中文提示

**操作**：不選年月（或故意不送 year/month）呼叫  
`POST /api/accounting/security-payroll/upload`（例如只送 file + type）。

**預期**：回傳 **400**，訊息為中文：**「請先選擇年份與月份再上傳計算」**（不要出現 500 或英文驗證錯誤）。

**實作**：後端 `year` / `month` 為 `Form(None)`，若 `year is None` 或 `month is None` 或 `month` 不在 1～12，直接 `HTTPException(400, detail="請先選擇年份與月份再上傳計算")`。前端未選年月時計算按鈕 disabled，且送出的 FormData 一定帶 year、month。

---

## 檔名與來源對照

| 情境 | 檔名（中文顯示） | ASCII fallback |
|------|------------------|----------------|
| GET export | 保全核薪_{year}_{month:02d}.xlsx | security_payroll_{year}_{month:02d}.xlsx |
| POST export | 同上（依 body.year / body.month） | 同上 |

Header 一律經 `build_content_disposition(ascii_name, unicode_name)` 產生，禁止直接 `filename="{中文}"`。
