# 5) 單元測試案例列表

## 測試檔位置

- `backend/tests/test_billing_days.py`：計費天數與月比例
- `backend/tests/test_health_reduction.py`：健保減免規則
- `backend/tests/test_insurance_billing.py`：試算整合（依加退保日、減免）
- `backend/tests/test_schedules.py`：排班 P0（有效指派限制、批量建立、統計正確性）

## 案例列表

### test_billing_days.py

| 案例 | 說明 |
|------|------|
| test_insured_days_single_month_no_cancel | 當月加保無退保：從加保日到月底（含加保日） |
| test_insured_days_single_month_with_cancel | 當月加退保：含加保日、不含退保日 |
| test_insured_days_cross_month | 跨月：當月整月計 |
| test_insured_days_enroll_after_month | 加保日在當月之後：0 天 |
| test_insured_days_cancel_before_month | 退保日在當月之前：0 天 |
| test_insured_days_last_day_of_month_enroll | 月底加保：當月 1 天 |
| test_insured_days_non_last_day_cancel | 月中退保：只算到退保日前一天 |
| test_insured_days_cancel_on_last_day | 退保日為當月最後一日：當月 30 天（不含退保日） |
| test_health_ratio_full_month_in_range | 健保：在加保區間內整月比例 1 |
| test_health_ratio_enroll_last_day_of_month | 健保：加保日為當月最後一日 → 比例 1 |
| test_health_ratio_cancel_not_last_day | 健保：退保日非當月最後一日 → 比例 0 |
| test_health_ratio_cancel_last_day_of_month | 健保：退保日為當月最後一日 → 比例 1 |
| test_health_ratio_enroll_after_month | 健保：加保日在當月之後 → 比例 0 |
| test_health_ratio_cancel_before_month | 健保：退保日在當月之前 → 比例 0 |
| test_daily_rate_from_monthly | 月費/30 = 日費 |
| test_labor_insurance_month_fee_prorated | 勞保按當月加保天數比例 |
| test_labor_insurance_month_fee_cross_month | 跨月：當月整月依日曆天數 |
| test_occupational_accident_month_fee | 職災按天數比例 |
| test_group_insurance_month_fee | 團保按天數比例 |
| test_labor_pension_month_fee | 勞退按天數比例 |
| test_is_last_day_of_month | 是否當月最後一日 |

### test_health_reduction.py

| 案例 | 說明 |
|------|------|
| test_no_reduction_without_condition | 無身障、非 65 歲眷屬：倍率 1 |
| test_disability_light | 身障輕度：0.75 |
| test_disability_moderate | 身障中度：0.5 |
| test_disability_severe | 身障重度：0 |
| test_disability_very_severe | 身障極重度：0 |
| test_senior_65_taoyuan_dependent | 65 歲眷屬桃園市：0 |
| test_senior_65_taipei_dependent | 65 歲眷屬台北市：0 |
| test_senior_64_no_city_reduction | 未滿 65 歲：不適用 65 歲補助 |
| test_senior_65_other_city_no_reduction | 65 歲非桃園/台北：不適用該條 |

### test_insurance_billing.py

| 案例 | 說明 |
|------|------|
| test_estimate_full_month_without_dates | 不傳年月：整月計費 |
| test_estimate_proration_mid_month_enroll | 月中加保：勞保等按天數、健保整月 |
| test_estimate_health_zero_when_cancel_not_last_day | 退保非月底：當月健保 0 |
| test_estimate_health_full_when_enroll_last_day | 加保日為當月最後一日：健保整月 |
| test_estimate_cross_month_full_january | 跨月：1 月整月在保 |
| test_estimate_with_persons_disability_reduction | 眷屬身障：健保明細有減免 |
| test_estimate_with_persons_senior_65_reduction | 眷屬 65 歲桃園市：健保個人 0 |

### test_schedules.py（排班 P0）

| 案例 | 說明 |
|------|------|
| test_shift_duration_hours_basic | 工時計算：同一天 start~end |
| test_shift_duration_hours_night_cross_midnight | 夜班跨日：end < start 視為跨日 |
| test_shift_duration_hours_missing_time | 缺 start 或 end 回傳 0 |
| test_eligible_employee_can_be_assigned | 有效指派：在案場有效期間內的員工可指派 |
| test_ineligible_employee_raises | 有效指派限制：不在期間內指派拋出 ScheduleAssignmentNotEligibleError |
| test_batch_create_shifts_for_month | 批量建立：該月幾天即幾筆 shift |
| test_monthly_shift_stats_correctness | 統計正確性：總班數、總工時、夜班數、84-1 標記 |

**執行**：需安裝 `pytest-asyncio`（已列入 `requirements.txt`）。`python run_tests.py` 會一併執行排班測試。

## 執行方式（Windows）

```powershell
cd backend
pip install pytest
python run_tests.py
# 或
python -m pytest tests/ -v --tb=short
```
