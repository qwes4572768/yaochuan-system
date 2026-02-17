# 6) 專案資料夾結構與啟動方式（Windows 10/11）

## 資料夾結構

```
資通系統/
├── backend/                      # 後端 FastAPI
│   ├── .env.example              # 環境變數範例
│   ├── .env                      # 本機設定（可自建，非版控）
│   ├── hr.db                     # SQLite 資料庫（執行遷移後產生）
│   ├── uploads/                  # 上傳 PDF 存放目錄
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── run_tests.py              # 執行單元測試
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/             # 001~004 遷移檔
│   ├── app/
│   │   ├── main.py                # 應用入口
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py              # Employee, Dependent, EmployeeDocument, InsuranceConfig, RateTable, RateItem, SalaryProfile, InsuranceMonthlyResult
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── crypto.py
│   │   ├── sensitive.py
│   │   ├── routers/               # employees, insurance, documents, reports, settings, rules, rate_tables
│   │   ├── rules/                 # health_reduction
│   │   └── services/              # billing_days, insurance_calc
│   ├── config/
│   │   ├── insurance_rules.yaml   # 假級距/費率（Demo 用）
│   │   ├── health_reduction_rules.yaml
│   │   └── rate_tables_seed.json  # 級距表種子（選用）
│   ├── scripts/
│   │   └── seed_rate_tables.py    # 匯入級距種子
│   └── tests/                     # 單元測試
├── frontend/                      # 前端 React + Vite + TypeScript
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts             # proxy /api -> 8000
│   └── src/
│       ├── App.tsx
│       ├── api.ts
│       ├── types.ts
│       ├── main.tsx
│       ├── index.css
│       ├── pages/                 # EmployeeList, EmployeeForm, EmployeeDetail, Reports, RateTables
│       └── utils/mask.ts
├── docs/                          # 本說明與 ERD、API、路由、計算、測試、啟動
└── README.md
```

## 啟動方式（Windows 10 或 11）

### 1. 環境需求

- Python 3.10+（建議 3.11）
- Node.js 18+（含 npm）
- 終端機：PowerShell 或 CMD

### 2. 後端

```powershell
cd 資通系統\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
# 若執行原則錯誤：Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API 文件：http://localhost:8000/docs  
- OpenAPI：http://localhost:8000/openapi.json  

### 3. 前端

另開一個終端機：

```powershell
cd 資通系統\frontend
npm install
npm run dev
```

- 前端：http://localhost:5173（會 proxy `/api` 到後端 8000）

### 4. 選用：級距種子

若要以 rate_tables 當假資料（否則用 YAML 假級距）：

```powershell
cd 資通系統\backend
.venv\Scripts\Activate.ps1
python scripts/seed_rate_tables.py
```

## Demo 流程檢查

1. **員工**：新增 → 編輯 → 列表搜尋 → 詳情 → 刪除（可先不做刪除，避免誤刪）。
2. **眷屬**：在員工表單設「眷屬數量」> 0，新增眷屬（最多 N 筆）；詳情頁看眷屬列表。
3. **PDF**：詳情頁選類型、上傳 PDF；下載連結可下載。
4. **試算**：詳情頁看當月試算（使用假級距：YAML 或已匯入 rate_tables）。
5. **報表**：報表頁選月份 → 下載「公司負擔總表」「員工個人負擔明細」「眷屬明細」三張 Excel；另可下載員工清單。
