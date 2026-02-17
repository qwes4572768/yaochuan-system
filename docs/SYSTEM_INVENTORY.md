# 系統功能盤點表（超詳細）

> 本文件由專案掃描產出，僅新增文件、未改動任何程式邏輯。  
> **list_sites** 的 total/items SQL、分頁、q、contract_active 已驗證，盤點表中標記「**已驗證不可改**」。

---

## 一、專案結構 Tree（摘要）

```
資通系統/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口、router 註冊
│   │   ├── config.py
│   │   ├── crud.py               # 所有 CRUD
│   │   ├── database.py
│   │   ├── models.py            # SQLAlchemy 模型
│   │   ├── schemas.py           # Pydantic 請求/回應
│   │   ├── crypto.py, sensitive.py
│   │   ├── routers/
│   │   │   ├── employees.py, documents.py, insurance.py
│   │   │   ├── rate_tables.py, reports.py, rules.py, settings.py, sites.py
│   │   ├── rules/
│   │   │   └── health_reduction.py
│   │   └── services/
│   │       ├── billing_days.py, insurance_calc.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 001_initial_schema.py ~ 006_sites_indexes.py
│   ├── config/                   # YAML、seed JSON
│   ├── tests/
│   │   ├── test_billing_days.py, test_health_reduction.py, test_insurance_billing.py
│   ├── scripts/                  # seed_sites, verify_sites_api
│   └── run_tests.py
├── frontend/src/
│   ├── App.tsx                   # 路由：/, /employees/new, /employees/:id, /employees/:id/edit, /reports, /rate-tables
│   ├── api.ts                    # employeesApi, insuranceApi, rateTablesApi, documentsApi, reportsApi
│   ├── pages/
│   │   ├── EmployeeList.tsx, EmployeeForm.tsx, EmployeeDetail.tsx
│   │   ├── Reports.tsx, RateTables.tsx
│   └── utils/errorMsg.ts, mask.ts
├── docs/                         # 01~06 + SYSTEM_INVENTORY
├── 啟動.bat
└── README.md
```

---

## 二、模組盤點（固定欄位）

### 模組：人事（員工 CRUD、薪資設定）

| 欄位 | 內容 |
|------|------|
| **子功能** | CRUD（列表/取得/新增/更新/刪除）、搜尋、分頁、薪資設定 GET/PUT |
| **Backend API** | **GET /api/employees** — query: `skip`, `limit`, `search`, `reveal_sensitive`。回傳 `List[EmployeeRead]`。404 無。 |
| | **GET /api/employees/{employee_id}** — query: `reveal_sensitive`。回傳 `EmployeeRead`。404 員工不存在。 |
| | **POST /api/employees** — body: `EmployeeCreate`（含 name, birth_date, national_id, reg_address, live_address, live_same_as_reg, salary_type, salary_value, insured_salary_level, enroll_date, cancel_date, dependent_count, notes, dependents[]）。回傳 201 EmployeeRead。 |
| | **PATCH /api/employees/{employee_id}** — body: `EmployeeUpdate`（皆選填）。回傳 EmployeeRead。404 員工不存在。 |
| | **DELETE /api/employees/{employee_id}** — 204。404 員工不存在。 |
| | **GET /api/employees/{employee_id}/salary-profile** — 回傳 `SalaryProfileRead \| null`。404 員工不存在。 |
| | **PUT /api/employees/{employee_id}/salary-profile** — body: `SalaryProfileUpdate`（salary_type, monthly_base, daily_rate, hourly_rate, overtime_eligible, calculation_rules）。回傳 SalaryProfileRead。404 員工不存在。 |
| **Backend 檔案** | router: `routers/employees.py`；crud: `crud.py`（get_employee, list_employees, create_employee, update_employee, delete_employee, get_salary_profile, upsert_salary_profile）；schemas: `schemas.py`（EmployeeBase, Create, Update, Read, SalaryProfile*）；models: `models.py`（Employee, SalaryProfile）；migrations: 001, 002, 004。 |
| **DB** | **employees**：id PK, name, birth_date, national_id, reg_address, live_address, live_same_as_reg, salary_type, salary_value, insured_salary_level, enroll_date, cancel_date, dependent_count, safety_pdf_path, contract_84_1_pdf_path, notes, created_at, updated_at。無額外索引（001 初版為舊欄位名，002 後對齊現有 model）。刪除：CASCADE 影響 dependents, documents, salary_profile, insurance_monthly_results, site_assignments。 |
| | **salary_profiles**：id PK, employee_id UK FK→employees, salary_type, monthly_base, daily_rate, hourly_rate, overtime_eligible, calculation_rules, created_at, updated_at。索引：employee_id。刪除：員工刪除時 CASCADE。 |
| **Frontend** | 路由：`/` 員工清單、`/employees/new` 新增、`/employees/:id` 詳情、`/employees/:id/edit` 編輯。元件：EmployeeList.tsx, EmployeeForm.tsx, EmployeeDetail.tsx。表單欄位：姓名、出生日、身分證、戶籍/居住地址、同戶籍、薪資類型/數值、投保級距、加退保日、眷屬數、備註；同戶籍勾選則居住地址鎖定帶入戶籍。驗證：身分證 10 碼格式（A123456789 / AB12345678）。操作：列表→搜尋（姓名或身分證後四碼）→點詳情/編輯/新增→存檔。 |
| **測試** | 無員工 CRUD 專用 E2E；計費與試算用員工資料由 test_insurance_billing 等間接覆蓋。 |
| **驗收方式** | `GET /api/employees?limit=10` 回傳陣列；或前端打開 `/` 可見員工清單並能新增一筆後再查 `GET /api/employees/{id}`。 |

---

### 模組：眷屬

| 欄位 | 內容 |
|------|------|
| **子功能** | CRUD（列表/新增/更新/刪除）、敏感欄位選填揭露 |
| **Backend API** | **GET /api/employees/{employee_id}/dependents** — query: `reveal_sensitive`。回傳 `List[DependentRead]`。404 員工不存在。 |
| | **POST /api/employees/{employee_id}/dependents** — body: `DependentCreate`（name, birth_date, national_id, relation, city, is_disabled, disability_level, notes）。回傳 201 DependentRead。404 員工不存在。 |
| | **PATCH /api/employees/{employee_id}/dependents/{dependent_id}** — body: `DependentUpdate`。回傳 DependentRead。404 眷屬不存在。 |
| | **DELETE /api/employees/{employee_id}/dependents/{dependent_id}** — 204。404 眷屬不存在。 |
| **Backend 檔案** | router: `routers/employees.py`；crud: `crud.py`（list_dependents_by_employee, create_dependent, update_dependent, delete_dependent, get_dependent）；schemas: `schemas.py`（DependentBase, Create, Update, Read）；models: `models.py`（Dependent）；migrations: 001, 002。 |
| **DB** | **dependents**：id PK, employee_id FK→employees CASCADE, name, birth_date, national_id, relation, city, is_disabled, disability_level, notes, created_at, updated_at。索引：employee_id。刪除：員工刪除時 CASCADE。 |
| **Frontend** | 在 EmployeeForm：眷屬區塊，依「眷屬數量」限制最多 N 張卡片；關係下拉（配偶/子女/父母/祖父母/其他）、縣市、是否身障、身障等級（勾選身障才顯示）。驗證：身分證格式同員工。操作：編輯員工→填眷屬數量→新增眷屬卡片→填寫→存檔。 |
| **測試** | test_health_reduction 覆蓋眷屬身障/65 歲減免情境；試算整合 test_insurance_billing 會帶眷屬。 |
| **驗收方式** | `POST /api/employees/1/dependents` body `{"name":"測試","relation":"子女"}` 回傳 201 含 id；`GET /api/employees/1/dependents` 可見該筆。 |

---

### 模組：計費（試算、保險結果落表、級距下拉）

| 欄位 | 內容 |
|------|------|
| **子功能** | 計算（試算）、查詢級距、薪資對級距、產生當月保險結果、查詢保險結果 |
| **Backend API** | **GET /api/insurance/brackets** — 回傳 `List[SalaryBracketItem]`（level, low, high）。 |
| | **GET /api/insurance/salary-to-level?salary=26400** — 回傳 `{ salary, insured_salary_level }`。 |
| | **POST /api/insurance/estimate** — body: `InsuranceEstimateRequest`（employee_id?, insured_salary_level?, dependent_count?, year?, month?）。回傳 `InsuranceEstimateResponse`（勞保/健保/職災/勞退/團保 breakdown、健保減免明細、total_employer/employee/total）。 |
| | **POST /api/insurance/monthly-result/generate** — query: `year`, `month`, `overwrite`。回傳 `{ year, month, year_month, employees_processed }`。 |
| | **GET /api/insurance/monthly-result** — query: `year_month`, `employee_id?`。回傳 `List[InsuranceMonthlyResultRead]`。 |
| **Backend 檔案** | router: `routers/insurance.py`；crud: `crud.py`（get_all_insurance_rules, list_insurance_monthly_results, upsert_insurance_monthly_result, delete_insurance_monthly_results_for_month）；schemas: `schemas.py`（InsuranceEstimateRequest/Response, InsuranceMonthlyResultRead, SalaryBracketItem 等）；services: `services/insurance_calc.py`（estimate_insurance, get_brackets, salary_to_level）、`services/billing_days.py`（天數/比例）；models: InsuranceMonthlyResult, InsuranceConfig；migrations: 004。 |
| **DB** | **insurance_config**：id PK, config_key UK, config_value, description, updated_at。**insurance_monthly_results**：id PK, employee_id FK CASCADE, year_month, item_type, employee_amount, employer_amount, gov_amount, created_at。索引：employee_id, year_month, item_type。 |
| **Frontend** | 員工詳情頁顯示「當月試算」：呼叫 insuranceApi.estimate(employee_id, year, month)；表單投保級距下拉來自 insuranceApi.brackets()、輸入薪資對級距 salaryToLevel。 |
| **測試** | **test_billing_days.py**：get_insured_days_in_month（含加保日不含退保日）、health_insurance_month_ratio（月底加保整月、非月底退保 0）、daily_rate、勞保/職災/團保/勞退按天數。**test_health_reduction.py**：身障輕中重極重度、65 歲眷屬減免。**test_insurance_billing.py**：estimate_insurance 整月、月中加保、退保非月底健保 0、月底加保健保整月、跨月、身障減免。執行：`cd backend && python run_tests.py` 或 `pytest tests/ -v --tb=short`。 |
| **驗收方式** | `POST /api/insurance/estimate` body `{"insured_salary_level":26400,"year":2025,"month":1}` 回傳含 labor_insurance/health_insurance 等；或前端員工詳情頁顯示當月試算金額。 |

---

### 模組：級距表（Rate Tables）

| 欄位 | 內容 |
|------|------|
| **子功能** | 列表（篩選 type）、當月有效、匯入（JSON/Excel/Word） |
| **Backend API** | **GET /api/rate-tables** — query: `type`（labor_insurance|health_insurance|occupational_accident|labor_pension）。回傳 `List[RateTableRead]`（含 items）。400 type 不合法。 |
| | **GET /api/rate-tables/effective** — query: `year`, `month`。回傳 `Dict[type, RateTableRead|null]`。 |
| | **POST /api/rate-tables/import** — body 或 file 二擇一。body: `RateTableImportPayload`（tables: [{ type, version, effective_from, effective_to?, total_rate?, note?, items: [{ level_name, salary_min, salary_max, insured_salary, employee_rate, employer_rate, gov_rate?, fixed_amount_if_any? }] }]）。file: .json / .xlsx / .docx。回傳 `List[RateTableRead]`。400 未提供或格式錯誤。 |
| **Backend 檔案** | router: `routers/rate_tables.py`；crud: `crud.py`（list_rate_tables, get_effective_rate_table, get_rate_table_by_id, get_all_insurance_rules 內建 build_rules_from_rate_tables）；schemas: RateTableRead, RateItemRead, RateTableImportPayload/Table/Item；models: RateTable, RateItem；migrations: 003。 |
| **DB** | **rate_tables**：id PK, type, version, effective_from, effective_to, total_rate, note。索引：type。**rate_items**：id PK, table_id FK CASCADE, level_name, salary_min, salary_max, insured_salary, employee_rate, employer_rate, gov_rate, fixed_amount_if_any。索引：table_id。刪除：刪 rate_table 時 rate_items CASCADE。 |
| **Frontend** | 路由 `/rate-tables`。元件 RateTables.tsx：選擇年月→檢視當月有效級距表、列出所有版本（可篩 type）、上傳 JSON/Excel 匯入。表單：年/月 select、類型篩選、file input。操作：選月份→看有效表→選檔案→匯入→重新載入。 |
| **測試** | 無級距表專用單元測試；試算依賴 crud.get_all_insurance_rules 與 rate_tables 邏輯。 |
| **驗收方式** | `GET /api/rate-tables/effective?year=2025&month=1` 回傳各 type 之 RateTableRead 或 null；或前端級距費率頁上傳一筆 JSON 後列表出現新版本。 |

---

### 模組：案場（Sites）

| 欄位 | 內容 |
|------|------|
| **子功能** | 案場 CRUD、分頁/搜尋/過濾、指派 CRUD、期間重疊驗證 |
| **Backend API** | **GET /api/sites** — **（已驗證不可改）** query: `page`, `page_size`, `load_assignments`, `q`（案場名稱/客戶/地址 部分符合）, `payment_method`, `is_841`, `contract_active`。回傳 `SiteListResponse`（items, total, page, page_size）。422 參數錯誤。 |
| | **GET /api/sites/by-employee/{employee_id}/assignments** — 回傳 `List[SiteAssignmentWithSite]`。404 員工不存在。 |
| | **GET /api/sites/{site_id}** — query: `load_assignments`。回傳 SiteRead。404 案場不存在。 |
| | **POST /api/sites** — body: SiteCreate（name, client_name, address, contract_start, contract_end?, monthly_amount, payment_method, receivable_day, notes?, daily_required_count?, shift_hours?, is_84_1?, night_shift_allowance?, bear_labor_insurance?, bear_health_insurance?, has_group_or_occupational?, rebate_type?, rebate_value?）。回傳 201 SiteRead。422 驗證失敗。 |
| | **PATCH /api/sites/{site_id}** — body: SiteUpdate（皆選填）。回傳 SiteRead。404/422。 |
| | **DELETE /api/sites/{site_id}** — 204。404。刪除案場時一併刪除其指派（CASCADE）。 |
| | **GET /api/sites/{site_id}/assignments** — 回傳 `List[SiteAssignmentWithEmployee]`。404 案場不存在。 |
| | **POST /api/sites/{site_id}/assignments** — body: SiteAssignmentCreate（employee_id, effective_from?, effective_to?, notes?）。回傳 201 SiteAssignmentRead。404 案場/員工不存在；409 重複指派或期間重疊。 |
| | **PATCH /api/sites/{site_id}/assignments/{assignment_id}** — body: SiteAssignmentUpdate。回傳 SiteAssignmentRead。404/409 期間重疊。 |
| | **DELETE /api/sites/{site_id}/assignments/{assignment_id}** — 204。404。 |
| **Backend 檔案** | router: `routers/sites.py`；crud: `crud.py`（list_sites【已驗證不可改】, get_site, create_site, update_site, delete_site, get_assignment, list_assignments_by_site, list_assignments_by_employee, check_assignment_period_overlap, create_assignment, update_assignment, delete_assignment, AssignmentPeriodOverlapError）；schemas: SiteBase/Create/Update/Read, SiteListResponse, SiteAssignment*；models: Site, SiteEmployeeAssignment；migrations: 005, 006。 |
| **DB** | **sites**：id PK, name, client_name, address, contract_start, contract_end, monthly_amount, payment_method, receivable_day, notes, daily_required_count, shift_hours, is_84_1, night_shift_allowance, bear_labor_insurance, bear_health_insurance, has_group_or_occupational, rebate_type, rebate_value, created_at, updated_at。索引：name, client_name, contract_end, payment_method（006）。**site_employee_assignments**：id PK, site_id FK CASCADE, employee_id FK CASCADE, effective_from, effective_to, notes, created_at。UK(site_id, employee_id)。索引：site_id, employee_id, effective_from, effective_to（006）。刪除策略：刪案場→指派 CASCADE；刪員工→指派 CASCADE。 |
| **Frontend** | 目前無案場專用頁面；API 已就緒，可透過 Swagger / Postman 或 scripts/verify_sites_api.py 驗收。 |
| **測試** | scripts/verify_sites_api.py 驗證 list_sites 分頁與過濾；README_SITES_VALIDATION.md 說明驗證流程。無案場 CRUD 單元測試。 |
| **驗收方式** | `GET /api/sites?page=1&page_size=20&q=關鍵字&contract_active=true` 回傳 total 與 items 一致（已驗證不可改）；或執行 `python backend/scripts/verify_sites_api.py`。 |

---

### 模組：報表（Reports）

| 欄位 | 內容 |
|------|------|
| **子功能** | 匯出 Excel（員工清單、眷屬清單、當月公司負擔、當月個人負擔） |
| **Backend API** | **GET /api/reports/export/employees** — 回傳 Excel stream。檔名 employees_{date}.xlsx。 |
| | **GET /api/reports/export/dependents** — 回傳 Excel stream。檔名 dependents_{date}.xlsx。 |
| | **GET /api/reports/export/monthly-burden** — query: `year`, `month`。回傳 Excel（公司負擔：勞保/健保/職災/勞退/團保 雇主、小計）。檔名 monthly_burden_YYYYMM.xlsx。 |
| | **GET /api/reports/export/personal-burden** — query: `year`, `month`。回傳 Excel（員工個人負擔：勞保+健保）。檔名 personal_burden_YYYYMM.xlsx。Content-Disposition 使用 ASCII 檔名避免編碼錯誤。 |
| **Backend 檔案** | router: `routers/reports.py`；crud: list_employees, get_all_insurance_rules；services: insurance_calc.estimate_insurance；無專用 schema（StreamingResponse）。 |
| **DB** | 僅讀取 employees, dependents, insurance 規則；無報表專用表。 |
| **Frontend** | 路由 `/reports`。元件 Reports.tsx：選擇年/月→三個按鈕「公司負擔總表」「員工個人負擔明細」「眷屬明細」→downloadReportExcel 下載。驗證：無。操作：選月份→點按鈕→瀏覽器下載 Excel。 |
| **測試** | 無報表匯出專用測試。 |
| **驗收方式** | `GET /api/reports/export/monthly-burden?year=2025&month=1` 回傳 xlsx；或前端報表頁選月份點「公司負擔總表」成功下載。 |

---

### 模組：檔案（Documents）

| 欄位 | 內容 |
|------|------|
| **子功能** | 上傳（安全查核 PDF、84-1 PDF）、列表、下載 |
| **Backend API** | **GET /api/documents/employee/{employee_id}** — 回傳 `List[DocumentRead]`。404 員工不存在。 |
| | **POST /api/documents/employee/{employee_id}/upload** — form: `document_type`（security_check|84_1）, `file`（PDF）。回傳 201 DocumentRead。400 type 或非 PDF 或超過大小；404 員工不存在。 |
| | **GET /api/documents/{doc_id}/download** — 回傳 FileResponse（application/pdf）。404 檔案不存在或已遺失。 |
| **Backend 檔案** | router: `routers/documents.py`；crud: add_document, get_document, list_documents_by_employee；schemas: DocumentRead；models: EmployeeDocument；config: max_upload_size_mb。 |
| **DB** | **employee_documents**：id PK, employee_id FK CASCADE, document_type, file_name, file_path, file_size, uploaded_at。索引：employee_id。刪除：員工刪除 CASCADE。 |
| **Frontend** | 員工詳情頁：檔案列表、上傳（選 security_check / 84_1、選檔）、10MB 限制提示、下載連結。驗證：前端檢查 PDF 類型與 10MB。操作：進入員工詳情→選類型→選 PDF→上傳→列表更新→點下載。 |
| **測試** | 無檔案上傳專用測試。 |
| **驗收方式** | `POST /api/documents/employee/1/upload` form-data document_type=security_check, file=xxx.pdf 回傳 201；`GET /api/documents/employee/1` 可見新筆；`GET /api/documents/{id}/download` 可下載。 |

---

### 模組：規則與設定（Rules / Settings）

| 欄位 | 內容 |
|------|------|
| **子功能** | 查詢健保減免規則、取得/更新保險設定 |
| **Backend API** | **GET /api/rules/health-reduction** — 回傳 `List[dict]`（YAML 規則）。 |
| | **GET /api/settings/insurance** — 回傳勞健保/職災/團保/勞退費率與級距（DB + YAML 補齊）。 |
| | **PUT /api/settings/insurance** — body: 部分 key（labor_insurance, health_insurance, …）物件。回傳更新後完整設定。400 不支援的 key 或非物件。 |
| **Backend 檔案** | router: `routers/rules.py`, `routers/settings.py`；rules: `rules/health_reduction.py`；crud: get_insurance_config, set_insurance_config, get_all_insurance_rules；config: health_reduction_rules.yaml, insurance_rules.yaml。 |
| **DB** | insurance_config（見計費模組）。 |
| **Frontend** | 未直接呼叫 rules；設定多為後台/試算內部使用。 |
| **測試** | test_health_reduction 覆蓋 apply_health_reduction 規則。 |
| **驗收方式** | `GET /api/rules/health-reduction` 回傳陣列；`GET /api/settings/insurance` 回傳各項費率物件。 |

---

### 模組：啟動與部署

| 欄位 | 內容 |
|------|------|
| **子功能** | 一鍵啟動、單元測試執行、種子與 API 驗證腳本 |
| **Backend** | 根目錄 `啟動.bat`：檢查 Python/npm、安裝依賴、啟動前後端、開瀏覽器。backend：1_install.bat, 2_start_backend.bat；run_tests.py 呼叫 pytest tests/ -v --tb=short。 |
| **Frontend** | 啟動器資料夾：一鍵啟動、僅前端/僅後端、安裝前後端、開啟系統網頁。 |
| **測試** | 見「計費」模組；執行：`cd backend && python run_tests.py`。 |
| **驗收方式** | 執行 `啟動.bat` 後可開啟 http://localhost:5173 並呼叫 http://localhost:8000/docs；或 `cd backend && python run_tests.py` 全部通過。 |

---

## 三、API 端點總表（完整）

| 方法 | 路徑 | 說明 | 回傳/錯誤 |
|------|------|------|------------|
| GET | / | 根 | message, docs |
| GET | /api/employees | 員工列表 | List[EmployeeRead] |
| GET | /api/employees/{id} | 單一員工 | EmployeeRead / 404 |
| POST | /api/employees | 新增員工 | 201 EmployeeRead |
| PATCH | /api/employees/{id} | 更新員工 | EmployeeRead / 404 |
| DELETE | /api/employees/{id} | 刪除員工 | 204 / 404 |
| GET | /api/employees/{id}/dependents | 眷屬列表 | List[DependentRead] / 404 |
| POST | /api/employees/{id}/dependents | 新增眷屬 | 201 DependentRead / 404 |
| PATCH | /api/employees/{id}/dependents/{did} | 更新眷屬 | DependentRead / 404 |
| DELETE | /api/employees/{id}/dependents/{did} | 刪除眷屬 | 204 / 404 |
| GET | /api/employees/{id}/salary-profile | 薪資設定 | SalaryProfileRead|null / 404 |
| PUT | /api/employees/{id}/salary-profile |  upsert 薪資設定 | SalaryProfileRead / 404 |
| GET | /api/documents/employee/{id} | 員工檔案列表 | List[DocumentRead] / 404 |
| POST | /api/documents/employee/{id}/upload | 上傳 PDF | 201 DocumentRead / 400,404 |
| GET | /api/documents/{doc_id}/download | 下載檔案 | FileResponse / 404 |
| GET | /api/insurance/brackets | 級距列表 | List[SalaryBracketItem] |
| GET | /api/insurance/salary-to-level | 薪資→級距 | { salary, insured_salary_level } |
| POST | /api/insurance/estimate | 試算 | InsuranceEstimateResponse |
| POST | /api/insurance/monthly-result/generate | 產生當月結果 | { year, month, year_month, employees_processed } |
| GET | /api/insurance/monthly-result | 查詢結果 | List[InsuranceMonthlyResultRead] |
| GET | /api/rate-tables | 級距表列表 | List[RateTableRead] / 400 |
| GET | /api/rate-tables/effective | 當月有效級距表 | Dict[type, RateTableRead|null] |
| POST | /api/rate-tables/import | 匯入級距表 | List[RateTableRead] / 400 |
| GET | /api/reports/export/employees | 員工清單 Excel | stream |
| GET | /api/reports/export/dependents | 眷屬清單 Excel | stream |
| GET | /api/reports/export/monthly-burden | 公司負擔 Excel | stream |
| GET | /api/reports/export/personal-burden | 個人負擔 Excel | stream |
| GET | /api/rules/health-reduction | 健保減免規則 | List[dict] |
| GET | /api/settings/insurance | 保險設定 | Dict |
| PUT | /api/settings/insurance | 更新保險設定 | Dict / 400 |
| GET | /api/sites | 案場列表（已驗證不可改） | SiteListResponse / 422 |
| GET | /api/sites/by-employee/{id}/assignments | 員工的案場指派 | List[SiteAssignmentWithSite] / 404 |
| GET | /api/sites/{id} | 單一案場 | SiteRead / 404 |
| POST | /api/sites | 新增案場 | 201 SiteRead / 422 |
| PATCH | /api/sites/{id} | 更新案場 | SiteRead / 404,422 |
| DELETE | /api/sites/{id} | 刪除案場 | 204 / 404 |
| GET | /api/sites/{id}/assignments | 案場指派列表 | List[SiteAssignmentWithEmployee] / 404 |
| POST | /api/sites/{id}/assignments | 新增指派 | 201 SiteAssignmentRead / 404,409,422 |
| PATCH | /api/sites/{id}/assignments/{aid} | 更新指派 | SiteAssignmentRead / 404,409,422 |
| DELETE | /api/sites/{id}/assignments/{aid} | 移除指派 | 204 / 404 |

---

## 四、README 可貼的 API 摘要

見本文件最末「附錄 A：README 可貼的 API 摘要」。

---

## 五、下一步建議（排班模組 P0）

見本文件最末「附錄 B：下一步建議（排班模組 P0）」。

---

## 附錄 A：README 可貼的 API 摘要

```markdown
### API 摘要

- **員工**：`GET/POST /api/employees`、`GET/PATCH/DELETE /api/employees/{id}`；眷屬 `GET/POST/PATCH/DELETE /api/employees/{id}/dependents/{did}`；薪資設定 `GET/PUT /api/employees/{id}/salary-profile`。
- **檔案**：`GET /api/documents/employee/{id}`、`POST /api/documents/employee/{id}/upload`（form: document_type, file）、`GET /api/documents/{doc_id}/download`。
- **保險試算**：`GET /api/insurance/brackets`、`GET /api/insurance/salary-to-level?salary=`、`POST /api/insurance/estimate`（body: employee_id?, insured_salary_level?, year?, month?）；結果落表：`POST /api/insurance/monthly-result/generate?year=&month=`、`GET /api/insurance/monthly-result?year_month=`。
- **級距表**：`GET /api/rate-tables`、`GET /api/rate-tables/effective?year=&month=`、`POST /api/rate-tables/import`（body 或 file .json/.xlsx/.docx）。
- **報表**：`GET /api/reports/export/employees`、`/dependents`、`/monthly-burden?year=&month=`、`/personal-burden?year=&month=`。
- **案場**：`GET/POST/PATCH/DELETE /api/sites`（列表支援 page, page_size, q, payment_method, is_841, contract_active）；`GET/POST/PATCH/DELETE /api/sites/{id}/assignments`；`GET /api/sites/by-employee/{id}/assignments`。
- **規則/設定**：`GET /api/rules/health-reduction`、`GET/PUT /api/settings/insurance`。
- **文件**：啟動後端後 `http://localhost:8000/docs` 可檢視 OpenAPI。
```

---

## 附錄 B：下一步建議（排班模組 P0）

1. **排班模組（P0）**  
   - 依案場與人力需求（daily_required_count、shift_hours）建立「班表」與「出勤」資料表（可關聯 site_employee_assignments、effective_from/to）。  
   - API：班表 CRUD、依案場/月份查詢、出勤登錄或匯入。  
   - 前端：案場列表/詳情頁（接現有 sites API）、排班月曆或列表、出勤勾選或批次匯入。  

2. **薪資計算銜接**  
   - 使用既有 salary_profile（月薪/日薪/時薪）與排班/出勤天數，計算當月薪資；可再與 insurance_monthly_result 整合做成本分析。  

3. **案場前端**  
   - 若尚未有案場管理頁，可新增路由 `/sites`、`/sites/:id`，呼叫現有 sites API，方便維護案場與指派，並為排班選案場鋪路。  

4. **維運**  
   - 保留 list_sites 之 total/items/q/contract_active 邏輯不變（已驗證）；新增功能以新端點或新參數擴充為宜。  

---

*文件產出日期：依掃描當日。盤點過程未改動任何程式邏輯。*
