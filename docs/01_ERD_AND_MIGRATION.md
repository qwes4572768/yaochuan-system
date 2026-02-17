# 1) 資料庫 ERD + Migration

## ERD（Mermaid）

```mermaid
erDiagram
    employees ||--o{ dependents : "1:N"
    employees ||--o{ employee_documents : "1:N"
    employees ||--o| salary_profiles : "1:1"
    employees ||--o{ insurance_monthly_results : "1:N"
    rate_tables ||--o{ rate_items : "1:N"
    insurance_config }  ..  : "key-value"
    sites ||--o{ schedules : "1:N"
    schedules ||--o{ schedule_shifts : "1:N"
    schedule_shifts ||--o{ schedule_assignments : "1:N"
    employees ||--o{ schedule_assignments : "1:N"

    employees {
        int id PK "employee_id 永久不變"
        string name
        date birth_date
        string national_id
        string reg_address
        string live_address
        bool live_same_as_reg
        string salary_type
        decimal salary_value
        decimal insured_salary_level
        date enroll_date
        date cancel_date
        int dependent_count
        string safety_pdf_path
        string contract_84_1_pdf_path
        text notes
        datetime created_at
        datetime updated_at
    }

    dependents {
        int id PK
        int employee_id FK
        string name
        date birth_date
        string national_id
        string relation
        string city
        bool is_disabled
        string disability_level
        string notes
        datetime created_at
        datetime updated_at
    }

    employee_documents {
        int id PK
        int employee_id FK
        string document_type
        string file_name
        string file_path
        int file_size
        datetime uploaded_at
    }

    salary_profiles {
        int id PK
        int employee_id FK UK
        string salary_type
        decimal monthly_base
        decimal daily_rate
        decimal hourly_rate
        bool overtime_eligible
        text calculation_rules
        datetime created_at
        datetime updated_at
    }

    insurance_monthly_results {
        int id PK
        int employee_id FK
        int year_month
        string item_type
        decimal employee_amount
        decimal employer_amount
        decimal gov_amount
        datetime created_at
    }

    insurance_config {
        int id PK
        string config_key UK
        text config_value
        string description
        datetime updated_at
    }

    rate_tables {
        int id PK
        string type
        string version
        date effective_from
        date effective_to
        decimal total_rate
        string note
    }

    rate_items {
        int id PK
        int table_id FK
        string level_name
        decimal salary_min
        decimal salary_max
        decimal insured_salary
        decimal employee_rate
        decimal employer_rate
        decimal gov_rate
        decimal fixed_amount_if_any
    }

    schedules {
        int id PK
        int site_id FK
        int year
        int month
        string status "draft/published/locked"
        text notes
        datetime created_at
        datetime updated_at
    }

    schedule_shifts {
        int id PK
        int schedule_id FK
        date date
        string shift_code "day/night/reserved"
        time start_time
        time end_time
        int required_headcount
        datetime created_at
    }

    schedule_assignments {
        int id PK
        int shift_id FK
        int employee_id FK
        string role "leader/post/normal"
        bool confirmed
        string notes
        datetime created_at
    }
```

## Migration 清單

| 版本 | 檔名 | 說明 |
|------|------|------|
| 001 | 001_initial_schema.py | 初版：employees, dependents, employee_documents, insurance_config |
| 002 | 002_employee_dependent_spec.py | 規格更新：欄位對齊 HR 規格（national_id, reg_address, enroll_date, cancel_date, dependent_count, dependents 身障等） |
| 003 | 003_rate_tables_and_items.py | rate_tables + rate_items（級距/費率依類型與生效區間） |
| 004 | 004_salary_profile_and_insurance_monthly_result.py | salary_profiles（薪資可擴充）、insurance_monthly_results（保險結果落表） |
| 005 | 005_sites_and_assignments.py | sites（案場）、site_employee_assignments（案場-員工指派，多對多） |
| 006 | 006_sites_indexes.py | sites / site_employee_assignments 常用查詢欄位索引 |
| 007 | 007_schedules.py | 排班 P0：schedules、schedule_shifts、schedule_assignments |

## 案場與指派刪除策略

- **刪除案場（sites）**：`site_employee_assignments` 外鍵 `ondelete="CASCADE"`，刪除案場時一併刪除其所有指派紀錄。
- **刪除員工（employees）**：`site_employee_assignments` 外鍵 `ondelete="CASCADE"`，刪除員工時一併刪除其所有案場指派紀錄（不阻擋員工刪除）。
- **唯一約束**：同一 `(site_id, employee_id)` 僅允許一筆指派（`uq_site_employee`）。

## 排班刪除策略（007）

- **刪除排班表（schedules）**：`schedule_shifts` 外鍵 `ondelete="CASCADE"`，刪除排班表時一併刪除所有班別與人員指派。
- **刪除班別（schedule_shifts）**：`schedule_assignments` 外鍵 `ondelete="CASCADE"`。
- **刪除員工（employees）**：`schedule_assignments` 外鍵 `ondelete="CASCADE"`。
- **指派規則**：僅能指派「在該案場有效期間內」的員工（依 `site_employee_assignments` 的 `effective_from` / `effective_to`）。

## 執行遷移（Windows）

若路徑含中文或出現編碼錯誤，請先設定 UTF-8 或將專案搬到英文路徑，詳見 [README § Alembic 遷移（Windows 路徑／編碼相容）](../README.md)。

```powershell
cd backend
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
chcp 65001
.venv\Scripts\Activate.ps1
python -m alembic upgrade head
```

## 種子資料（選用）

- 級距表假資料：`config/rate_tables_seed.json`
- 執行：`python scripts/seed_rate_tables.py`（需先 `alembic upgrade head`）
- 未匯入時，試算會使用 `config/insurance_rules.yaml` 預設級距
