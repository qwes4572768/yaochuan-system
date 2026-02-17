# 2) API 規格（OpenAPI）

## 取得 OpenAPI JSON / 互動文件

- **OpenAPI JSON**：`GET http://localhost:8000/openapi.json`（後端啟動後）
- **Swagger UI**：`http://localhost:8000/docs`
- **ReDoc**：`http://localhost:8000/redoc`

## API 模組與路徑摘要

### 員工 (employees)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/employees | 列表（skip, limit, search 姓名） |
| GET | /api/employees/{id} | 單筆（?reveal_sensitive=1 可取得明文） |
| POST | /api/employees | 新增 |
| PATCH | /api/employees/{id} | 更新 |
| DELETE | /api/employees/{id} | 刪除 |
| GET | /api/employees/{id}/dependents | 眷屬列表 |
| POST | /api/employees/{id}/dependents | 新增眷屬 |
| PATCH | /api/employees/{id}/dependents/{dep_id} | 更新眷屬 |
| DELETE | /api/employees/{id}/dependents/{dep_id} | 刪除眷屬 |
| GET | /api/employees/{id}/salary-profile | 薪資設定（可選） |
| PUT | /api/employees/{id}/salary-profile | 新增/更新薪資設定 |

### 保險試算 (insurance)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/insurance/brackets | 投保薪資級距下拉 |
| GET | /api/insurance/salary-to-level?salary= | 輸入金額對應級距 |
| POST | /api/insurance/estimate | 試算（body: employee_id?, insured_salary_level?, dependent_count?, year?, month?） |
| POST | /api/insurance/monthly-result/generate?year=&month=&overwrite= | 產生當月保險結果落表 |
| GET | /api/insurance/monthly-result?year_month=&employee_id= | 查詢保險結果（會計用） |

### 檔案 (documents)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/documents/employee/{id} | 該員工檔案列表 |
| POST | /api/documents/employee/{id}/upload | 上傳 PDF（Form: document_type, file） |
| GET | /api/documents/{doc_id}/download | 下載檔案 |

### 報表 (reports)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/reports/export/employees | 員工清單 Excel |
| GET | /api/reports/export/dependents | 眷屬清單 Excel |
| GET | /api/reports/export/monthly-burden?year=&month= | 當月公司負擔 Excel |
| GET | /api/reports/export/personal-burden?year=&month= | 當月員工個人負擔 Excel |

### 設定 (settings)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/settings/insurance | 費率/級距設定（DB 或 YAML） |
| PUT | /api/settings/insurance | 更新費率設定 |

### 級距表 (rate-tables)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/rate-tables?type= | 級距表列表 |
| GET | /api/rate-tables/effective?year=&month= | 當月有效級距表 |
| POST | /api/rate-tables/import | 匯入 JSON 或 Excel（body 或 file） |

### 規則 (rules)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/rules/health-reduction | 健保減免規則 |

### 案場管理 (sites)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/sites | 案場列表（分頁：page, page_size；搜尋：q, payment_method, is_841, contract_active） |
| GET | /api/sites/by-employee/{employee_id}/assignments | 某員工被指派的案場列表 |
| GET | /api/sites/{site_id} | 單一案場 |
| POST | /api/sites | 新增案場 |
| PATCH | /api/sites/{site_id} | 更新案場 |
| DELETE | /api/sites/{site_id} | 刪除案場（CASCADE 刪除其指派） |
| GET | /api/sites/{site_id}/assignments | 案場底下的指派列表（含員工姓名） |
| POST | /api/sites/{site_id}/assignments | 新增指派（body: employee_id, effective_from?, effective_to?, notes?） |
| PATCH | /api/sites/{site_id}/assignments/{assignment_id} | 更新指派（期間不可與同案場同員工其他指派重疊） |
| DELETE | /api/sites/{site_id}/assignments/{assignment_id} | 移除指派 |

**案場欄位摘要**：name, client_name, address, contract_start, contract_end, monthly_amount, payment_method（transfer/cash/check）, receivable_day（1–31）, notes；人力：daily_required_count, shift_hours, is_84_1, night_shift_allowance；成本：bear_labor_insurance, bear_health_insurance, has_group_or_occupational, rebate_type（amount/percent）, rebate_value。

**錯誤回傳**：404 資源不存在、409 衝突（重複指派或期間重疊）、422 參數驗證失敗；皆為 `{ "detail": "訊息" }`。

### 排班 P0 (schedules)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/schedules | 排班表列表（?site_id=, ?year=, ?month=） |
| GET | /api/schedules/{schedule_id} | 單一排班表 |
| POST | /api/schedules | 新增排班表（body: site_id, year, month, status?, notes?） |
| PATCH | /api/schedules/{schedule_id} | 更新排班表（status?, notes?） |
| DELETE | /api/schedules/{schedule_id} | 刪除排班表（CASCADE 班別與指派） |
| GET | /api/schedules/{schedule_id}/shifts | 班別列表 |
| POST | /api/schedules/{schedule_id}/shifts | 新增一筆班別（body: date, shift_code, start_time?, end_time?, required_headcount?） |
| POST | /api/schedules/{schedule_id}/shifts/batch | 批量建立該月班別（body: shift_code, start_time?, end_time?, required_headcount?） |
| PATCH | /api/schedules/{schedule_id}/shifts/{shift_id} | 更新班別 |
| DELETE | /api/schedules/{schedule_id}/shifts/{shift_id} | 刪除班別 |
| GET | /api/schedules/{schedule_id}/shifts/{shift_id}/assignments | 班別底下的人員指派 |
| POST | /api/schedules/{schedule_id}/shifts/{shift_id}/assignments | 指派員工到班別（body: employee_id, role?, confirmed?, notes?）；僅能指派在案場有效期間內的員工 |
| PATCH | /api/schedules/{schedule_id}/shifts/{shift_id}/assignments/{assignment_id} | 更新指派 |
| DELETE | /api/schedules/{schedule_id}/shifts/{shift_id}/assignments/{assignment_id} | 移除指派 |
| GET | /api/schedules/stats/monthly?year_month=&employee_id= | 產出員工某月排班統計（總班數、總工時、夜班數、是否 84-1 案場） |

**排班欄位摘要**：schedules（site_id, year, month, status: draft/published/locked, notes）；schedule_shifts（date, shift_code: day/night/reserved, start_time, end_time, required_headcount）；schedule_assignments（employee_id, role: leader/post/normal, confirmed, notes）。

**錯誤回傳**：404 資源不存在、409 該員工在此班別日期不在案場有效指派期間內、422 參數驗證失敗。
