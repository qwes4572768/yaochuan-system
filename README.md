# 保全公司管理系統 · 人事管理 HR Demo

第一階段：人事管理 MVP；排班 P0 已上線。可跑 Demo 含員工/眷屬 CRUD、勞健保試算（假級距）、PDF 上傳下載、Excel 三張表匯出、案場管理、排班（排班表/班別/人員指派與月統計）。

---

## 1) 文件索引

| 文件 | 說明 |
|------|------|
| [docs/01_ERD_AND_MIGRATION.md](docs/01_ERD_AND_MIGRATION.md) | 資料庫 ERD（Mermaid）+ Migration 清單與執行方式 |
| [docs/02_API_SPEC.md](docs/02_API_SPEC.md) | API 規格（OpenAPI 取得方式與路徑摘要） |
| [docs/03_FRONTEND_ROUTES.md](docs/03_FRONTEND_ROUTES.md) | 前端頁面路由（員工列表/新增/編輯/詳情/報表/級距費率） |
| [docs/04_CALCULATION_MODULES.md](docs/04_CALCULATION_MODULES.md) | 計算模組（rules + rate tables、計費邏輯、假級距） |
| [docs/05_UNIT_TEST_CASES.md](docs/05_UNIT_TEST_CASES.md) | 單元測試案例列表與執行方式 |
| [docs/06_PROJECT_STRUCTURE_AND_STARTUP.md](docs/06_PROJECT_STRUCTURE_AND_STARTUP.md) | 專案資料夾結構與 Windows 啟動方式 |

---

## 2) 專案結構摘要

```
資通系統/
├── backend/                 # FastAPI + SQLAlchemy + Alembic
│   ├── app/                  # main, models, schemas, crud, routers, rules, services
│   ├── config/               # insurance_rules.yaml（假級距）, health_reduction_rules.yaml, rate_tables_seed.json
│   ├── alembic/versions/    # 001~007 遷移（007 排班 P0）
│   ├── scripts/              # seed_rate_tables.py
│   └── tests/                # test_billing_days, test_health_reduction, test_insurance_billing, test_schedules
├── frontend/                 # React 18 + TypeScript + Vite + Tailwind
│   └── src/pages/             # EmployeeList, EmployeeForm, EmployeeDetail, Reports, RateTables
├── docs/                     # 上述 01~06 文件
└── README.md
```

---

## 3) 啟動方式（Windows 10 / 11）

### 環境需求

- **Python 3.10+**（建議 3.11）
- **Node.js 18+**（含 npm）
- 終端機：PowerShell 或 CMD

### 後端

```powershell
cd 資通系統\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
# 若出現執行原則錯誤：Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Alembic 遷移（Windows 路徑／編碼相容）

若本機路徑含中文或遷移執行失敗，可依下列方式處理。

**方式一：設定 UTF-8 後再執行（PowerShell）**

```powershell
cd 資通系統\backend
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
chcp 65001
.venv\Scripts\Activate.ps1
python -m alembic upgrade head
```

**方式二：CMD**

```cmd
cd 資通系統\backend
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
chcp 65001
.venv\Scripts\activate.bat
python -m alembic upgrade head
```

**若仍失敗：建議將專案搬到英文路徑**

- 專案路徑含中文（例如 `桌面\資通系統`）時，部分 Windows 環境下 Python／Alembic 可能因編碼或路徑長度出錯。
- 建議將整個專案複製到英文路徑，例如：`C:\projects\hr-system`，再於該目錄執行上述 `alembic upgrade head`。
- `alembic/env.py` 已改為使用 `pathlib` 解析路徑並將專案根目錄加入 `sys.path`，可減少對「目前工作目錄」的依賴。

- **API 文件**：http://localhost:8000/docs  
- **OpenAPI JSON**：http://localhost:8000/openapi.json  

### 前端（另開終端機）

```powershell
cd 資通系統\frontend
npm install
npm run dev
```

- **前端**：http://localhost:5173（會 proxy `/api` 到後端 8000）

### 選用：級距種子（假資料）

未匯入時，試算使用 `config/insurance_rules.yaml` 假級距；若要改用 rate_tables：

```powershell
cd 資通系統\backend
.venv\Scripts\Activate.ps1
python scripts/seed_rate_tables.py
```

---

## 4) Demo 流程（完整可跑）

1. **員工新增/編輯/刪除/查詢**
   - 員工清單（/）：搜尋姓名或身分證後四碼；檢視、編輯、刪除。
   - 新增員工（/employees/new）：填寫基本資料、戶籍/居住地址、同戶籍勾選、投保級距、加退保日、眷屬數量。
   - 編輯（/employees/:id/edit）：同表單；眷屬區塊依「眷屬數量」顯示，可新增眷屬（最多 N 筆）。

2. **眷屬新增/編輯（依 dependent_count 限制）**
   - 在員工表單設「眷屬數量」> 0，下方出現眷屬區塊；按「新增眷屬」新增，最多 N 筆；可移除單筆眷屬。

3. **上傳/下載 PDF**
   - 員工詳情（/employees/:id）：選擇「安全查核 PDF」或「84-1 PDF」→ 選擇檔案 → 上傳（僅 application/pdf，單檔最大 10MB）；已上傳檔案可點連結下載。

4. **選月份 → 產生當月試算（假級距）**
   - 詳情頁：顯示「當月費用試算」（使用 `insurance_rules.yaml` 或已匯入的 rate_tables）。
   - 試算 API 可帶 year、month；報表匯出時會依選定年月計算。

5. **匯出 Excel（三張表）**
   - 報表頁（/reports）：選擇「年」「月」後：
     - **公司負擔總表**：當月勞保/健保/職災/勞退/團保雇主負擔。
     - **員工個人負擔明細**：當月每位員工勞保+健保個人負擔。
     - **眷屬明細**：全部眷屬清單。
   - 另可下載「員工清單」Excel。

---

## 5) 單元測試

```powershell
cd backend
pip install pytest
python run_tests.py
# 或
python -m pytest tests/ -v --tb=short
```

案例列表見 [docs/05_UNIT_TEST_CASES.md](docs/05_UNIT_TEST_CASES.md)。

---

## 6) 案場管理 API 摘要

案場管理模組提供案場 CRUD 與案場-員工指派（多對多）。完整路徑與錯誤碼見 [docs/02_API_SPEC.md](docs/02_API_SPEC.md)。

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/sites | 案場列表（分頁：page, page_size；搜尋：q, payment_method, is_841, contract_active） |
| GET | /api/sites/{site_id} | 單一案場 |
| POST | /api/sites | 新增案場 |
| PATCH | /api/sites/{site_id} | 更新案場 |
| DELETE | /api/sites/{site_id} | 刪除案場（一併刪除其指派 CASCADE） |
| GET | /api/sites/{site_id}/assignments | 案場底下的指派列表 |
| POST | /api/sites/{site_id}/assignments | 新增指派 |
| GET | /api/sites/by-employee/{employee_id}/assignments | 某員工被指派的案場列表 |

**案場欄位**：案場名稱、客戶名稱、案場地址、合約起始/結束日、每月合約金額、收款方式（transfer/cash/check）、每月應收日（1–31）、備註；人力：每日需要人數、每班別工時、是否 84-1 案場、夜班加給；成本：是否負擔勞保/健保公司負擔、是否有團保或職災、案場回饋（amount/percent 與數值）。

**新增案場範例 request body（POST /api/sites）**：

```json
{
  "name": "A 棟大樓保全",
  "client_name": "○○物業",
  "address": "台北市信義區信義路一段 1 號",
  "contract_start": "2026-01-01",
  "contract_end": "2026-12-31",
  "monthly_amount": 150000,
  "payment_method": "transfer",
  "receivable_day": 5,
  "notes": "",
  "daily_required_count": 2,
  "shift_hours": 12,
  "is_84_1": true,
  "night_shift_allowance": 500,
  "bear_labor_insurance": true,
  "bear_health_insurance": true,
  "has_group_or_occupational": false,
  "rebate_type": "percent",
  "rebate_value": 5
}
```

**新增指派範例（POST /api/sites/{site_id}/assignments）**：

```json
{
  "employee_id": 1,
  "effective_from": "2026-01-01",
  "effective_to": null,
  "notes": ""
}
```

**錯誤回傳**：404 資源不存在、409 衝突（如該員工已指派至此案場或指派期間重疊）、422 參數驗證失敗；格式皆為 `{ "detail": "訊息" }`。

---

## 6.1) 排班 API 摘要（P0）

排班模組提供：排班表 CRUD（某案場某年某月）、班別 CRUD（可批量建立一整月）、人員指派到班別（僅能指派在案場有效期間內的員工）、月統計（總班數、總工時、夜班數，供薪資/會計使用）。84-1 案場在統計中會標記。

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/schedules | 排班表列表（site_id, year, month） |
| POST | /api/schedules | 新增排班表（site_id, year, month, status, notes） |
| GET | /api/schedules/{id}/shifts | 班別列表 |
| POST | /api/schedules/{id}/shifts | 新增一筆班別 |
| POST | /api/schedules/{id}/shifts/batch | 批量建立該月班別 |
| POST | /api/schedules/{id}/shifts/{shift_id}/assignments | 指派員工到班別（須在案場有效期間內） |
| GET | /api/schedules/stats/monthly?year_month= | 員工某月排班統計 |

詳見 [docs/02_API_SPEC.md](docs/02_API_SPEC.md) 排班 P0 一節。遷移 007：`alembic upgrade head` 後即生效。

---

## 7) 後續：匯入最新級距

Demo 跑通後，可：

- 在「級距費率」頁（/rate-tables）上傳 JSON 或 Excel 匯入級距；或
- 編輯 `config/rate_tables_seed.json` 後執行 `python scripts/seed_rate_tables.py`；或
- 使用 PUT /api/settings/insurance 更新費率設定。

試算與報表會依「計算月份」自動套用當月有效級距表（rate_tables）；無則使用 YAML 預設。
