# 4) 計算模組（rules + rate tables）

## 規則與資料來源

| 模組 | 用途 | 資料來源 |
|------|------|----------|
| **費率/級距** | 勞保、健保、職災、勞退級距與費率、公司/個人/政府比例 | rate_tables + rate_items（依計算月份有效版本）；缺則 insurance_config；再缺則 config/insurance_rules.yaml |
| **健保減免** | 65 歲眷屬縣市補助、身障減免 | config/health_reduction_rules.yaml；內建 _default_rules() |

## 計費邏輯（billing_days + insurance_calc）

- **健保**：以「月」計；加保日為當月最後一日仍算整月；退保日非當月最後一日則當月健保為 0。
- **勞保 / 職災 / 團保 / 勞退**：以天數計；(月費/30)×當月加保天數；**含加保日、不含退保日**。
- **試算入口**：`app/services/insurance_calc.estimate_insurance(rules, year, month, enroll_date, cancel_date, ...)`；rules 由 `crud.get_all_insurance_rules(db, year, month)` 取得（會自動套用當月有效 rate_tables）。

## 純函式（billing_days）

- `get_insured_days_in_month(year, month, enroll_date, cancel_date)`：當月加保天數
- `is_last_day_of_month(d)`：是否當月最後一日
- `health_insurance_month_ratio(...)`：健保當月比例 0 或 1
- `daily_rate_from_monthly(monthly_total)`：月費/30
- `labor_insurance_month_fee(...)`、`occupational_accident_month_fee(...)`、`group_insurance_month_fee(...)`、`labor_pension_month_fee(...)`：各項當月費用

## 假級距資料（Demo）

- 未匯入 rate_tables 時，使用 `config/insurance_rules.yaml`（勞保級距、健保/職災/勞退費率與比例）。
- 匯入範例：`config/rate_tables_seed.json`，執行 `python scripts/seed_rate_tables.py`。
