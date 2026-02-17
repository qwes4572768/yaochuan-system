# 勞健保計算方式詳細說明與級距 Excel 對應

## 一、費率／級距資料來源（誰先誰後）

試算時「規則」的取得順序如下：

1. **預設**：讀取 `config/insurance_rules.yaml`（內建勞保級距、費率、負擔比例等）。
2. **設定表**：若 DB 的 `insurance_config` 有對應 key，會用 JSON 覆蓋該類型。
3. **計算月份 + 級距表**：若 API 有帶 **year, month**（例如員工詳情試算、報表），會再以 **當月有效之 rate_tables** 覆蓋對應類型。

因此：**有上傳勞健保級距 Excel 且匯入成功後，在「有帶計算月份」的試算／報表裡，會以 DB 的級距表為準**；若該類型在 DB 沒有當月有效的表，才用 YAML（或設定表）。

---

## 二、試算時「規則」結構（每種類型用到的欄位）

從 `app/services/insurance_calc.py` 與 `app/crud.py` 的 `build_rules_from_rate_tables` 整理如下。

### 1. 勞保（labor_insurance）

| 欄位 | 來源 | 說明 | 預設（YAML） |
|------|------|------|----------------|
| rate | 級距表 `total_rate` 或 YAML | 勞保費率（含就保，如 11.5%） | 0.115 |
| employer_ratio | 級距表**第一筆** item 的 `employer_rate` | 雇主負擔比例 | 0.7 |
| employee_ratio | 級距表**第一筆** item 的 `employee_rate` | 員工負擔比例 | 0.2 |
| government_ratio | 級距表**第一筆** item 的 `gov_rate` | 政府負擔比例 | 0.1 |
| brackets | 級距表**所有** items | `[ (salary_min, salary_max, insured_salary), ... ]` | YAML 內 brackets |

**計算公式（整月）：**

- 投保薪資級距 = 員工的 `insured_salary_level`（或依薪資對 brackets 對應）
- 月勞保總額 = 投保薪資級距 × rate（四捨五入到小數 2 位）
- 雇主 = 月勞保總額 × employer_ratio  
- 員工 = 月勞保總額 × employee_ratio  
- 政府 = 月勞保總額 × government_ratio  

**加退保按天數時：**

- 當月加保天數 = `get_insured_days_in_month(year, month, enroll_date, cancel_date)`（含加保日、不含退保日）
- **整月在保**（加保天數 = 當月日曆天數，如 2 月 28 天、1 月 31 天）→ 收**整月**費用，不以 30 天換算。
- **未滿整月**（例如只上 15 天）→ 當月勞保費 = (月勞保總額 / 30) × 當月加保天數（四捨五入到 2 位）
- 再依 employer_ratio / employee_ratio 拆成雇主、員工。

---

### 2. 健保（health_insurance）

| 欄位 | 來源 | 說明 | 預設（YAML） |
|------|------|------|----------------|
| rate | 級距表 `total_rate` 或 YAML | 健保費率 | 0.0517 |
| employer_ratio | 級距表**第一筆** item 的 `employer_rate` | 雇主負擔比例 | 0.6 |
| employee_ratio | 級距表**第一筆** item 的 `employee_rate` | 員工負擔比例 | 0.3 |
| max_dependents_count | 固定 | 眷屬最多計入人數 | 3 |

**計算公式（整月）：**

- 投保級距 = 與勞保相同（同一個 `lab_level`）
- 計費人數 = 1（本人）+ min(眷屬數, 3)
- 每人健保費 = 投保級距 × rate（四捨五入）
- 月健保總額 = 每人健保費 × 計費人數
- 雇主 = 月健保總額 × employer_ratio  
- 員工 = 月健保總額 × employee_ratio（若有本人+眷屬資料，會再套**健保減免規則**，見下）

**健保減免（rules）：**

- 規則來自 `config/health_reduction_rules.yaml`（例如：六都 65 歲以上眷屬補助、身障補助）。
- 每人先算「原本個人負擔」，再依規則乘上倍率（0~1）得到「減免後個人負擔」；公司負擔不因減免變動。

**加退保時：**

- 健保當月比例 = `health_insurance_month_ratio(...)`：  
  - 月底加保 → 當月算整月（1）；非月底退保 → 當月 0；其餘在加保區間內為 1。  
- 當月健保費 = 上述整月金額 × 當月比例。

---

### 3. 職災（occupational_accident）

| 欄位 | 來源 | 說明 | 預設（YAML） |
|------|------|------|----------------|
| rate | 級距表 `total_rate` 或 YAML | 職災費率 | 0.0022 |
| employer_ratio | 級距表**第一筆** item 的 `employer_rate` | 通常 1（全雇主） | 1 |

**計算公式：**

- 月職災費 = 投保薪資級距 × rate（全雇主）
- 加退保時：整月在保收整月；未滿整月則 (月職災費 / 30) × 當月加保天數。

---

### 4. 勞退 6%（labor_pension）

| 欄位 | 來源 | 說明 | 預設（YAML） |
|------|------|------|----------------|
| employer_ratio | 級距表**第一筆** item 的 `employer_rate` | 提繳比例 | 0.06 |

**計算公式：**

- 月勞退額 = 投保薪資級距 × employer_ratio（全雇主）
- 加退保時：整月在保收整月；未滿整月則 (月勞退額 / 30) × 當月加保天數。

---

### 5. 團保（group_insurance）

- 預設每人 0，或由員工欄位/參數帶入 `group_insurance_fee`。
- 加退保時：當月團保 = (月團保費 / 30) × 當月加保天數。

---

## 三、級距「對應」怎麼跑（投保薪資級距從哪來）

1. 若員工有 **insured_salary_level**（投保薪資級距），直接用它當「投保薪資」。
2. 若沒有級距但有 **salary_input**（薪資輸入），則用 **勞保的 brackets** 對應：  
   - `_find_bracket(salary, brackets)`：找 `salary_min <= 薪資 <= salary_max` 的那一列，取該列的 **投保薪資**（即 brackets 的第三個值，或 rate_items 的 `insured_salary` / `salary_max`）。  
3. 若都沒有，預設 26400。

**結論：勞保的 brackets（級距區間 + 投保薪資）來自：**

- 有帶 year/month 且 DB 有當月有效的 `labor_insurance` 級距表 → 用**你上傳的級距 Excel 匯入後的那張表**。  
- 否則用 YAML 的 `labor_insurance.brackets`。

健保、職災、勞退**沒有**在試算時用「多筆級距區間」對應薪資，只用到該類型級距表裡的 **total_rate** 以及**第一筆** item 的 **employer_rate / employee_rate / gov_rate**；勞保才用整張 brackets 做「薪資 → 投保級距」的對應。

---

## 四、上傳的「勞健保級距 Excel」有沒有對應上？

### 4.1 級距 Excel 是給誰用的？

- 前端「級距費率」頁上傳的 **Excel（.xlsx）** 是給 **rate_tables 匯入**用的。  
- 匯入後會寫入 DB：`rate_tables`（主檔） + `rate_items`（級距明細）。  
- 試算／報表若有帶 **計算月份（year, month）**，會用 **當月有效** 的這幾張表來覆蓋 YAML。

所以：**有上傳並匯入成功，且生效日有涵蓋你要試算的月份，就會對應上。**

### 4.2 Excel 格式要求（系統實際怎麼解析）

- **一個工作表（Sheet）對應一張級距表**（一種 type）。  
- **第一列**：表頭，需有 **type** 或 **類型** 欄（必填）。  
- **type／類型 欄的「值」** 只能是以下四種英文代碼其一：  
  `labor_insurance`、`health_insurance`、`occupational_accident`、`labor_pension`  
- 同一列（或第二列）可放：**version**、**effective_from**、**effective_to**、**total_rate**、**note**。  
- **級距明細**從下一列開始，表頭需含（英文或部分中文依實作）：  

| 系統欄位 | Excel 表頭可接受 | 說明 |
|----------|------------------|------|
| salary_min | salary_min、min、**下限** | 薪資下限（含） |
| salary_max | salary_max、max、**上限** | 薪資上限（含） |
| insured_salary | insured、level、**投保**、**級距** | 投保薪資級距（勞保用；可空則以 salary_max 計） |
| employee_rate | employee、**個人** | 個人負擔比例 |
| employer_rate | employer、company、**公司** | 公司負擔比例 |
| gov_rate | gov、**政府** | 政府負擔比例（可空） |

- **Excel 與 Word .docx** 匯入皆支援上述**英文與中文**表頭；Excel 解析會先找英文關鍵字，找不到再找中文（下限、上限、投保、級距、個人、公司、政府），因此您上傳的級距 Excel 無論用英文或中文欄位名都能對應上。

### 4.3 如何確認「有對應上」

1. **匯入後**：到「級距費率」頁，選計算月份，看該月「有效之級距表」是否出現你剛匯入的 type（例如 labor_insurance）。  
2. **試算**：在員工詳情選**同一個計算月份**做當月費用試算，看勞保的級距與金額是否與你 Excel 的級距、費率一致。  
3. **API**：`GET /api/rate-tables/effective?year=2025&month=1` 可查該月各 type 有效表；若回傳的勞保表內容與你 Excel 一致，即表示有對應上。

### 4.4 常見對不上的原因

- **effective_from / effective_to** 沒有涵蓋你要試算的 year–month，所以當月有效表仍是舊表或 YAML。  
- **type** 打錯（例如打成 labour_insurance 或少字），該 Sheet 會被略過。  
- Excel 表頭與程式要求不符（缺 type、缺 salary_min/salary_max 等），導致解析不到或 items 為空。  
- 勞保只有 **brackets** 會整張用於「薪資→級距」；健保/職災/勞退只用 **total_rate** 和**第一筆**的負擔比例，若 Excel 只改某一筆而沒改 total_rate 或第一筆，可能和預期不符。

---

## 五、總結對照表

| 項目 | 計算方式 | 級距/費率來源（有帶 year/month 時） |
|------|----------|-------------------------------------|
| 勞保 | 投保級距×費率，再依雇主/員工/政府比例分攤；加退保按天數/30 | DB 當月有效 labor_insurance 表（brackets + total_rate + 第一筆比例） |
| 健保 | 投保級距×費率×(1+眷屬數)，再依雇主/員工比例；可套減免規則；加退保按月底規則 | DB 當月有效 health_insurance 表（total_rate + 第一筆比例） |
| 職災 | 投保級距×費率，全雇主；加退保按天數/30 | DB 當月有效 occupational_accident 表 |
| 勞退 | 投保級距×6%，全雇主；加退保按天數/30 | DB 當月有效 labor_pension 表（第一筆 employer_rate） |
| 團保 | 每人固定金額；加退保按天數/30 | 預設 0 或員工/參數帶入 |

**你上傳的勞健保級距 Excel**：匯入後會寫入上述 DB 級距表；**有指定計算月份且生效日涵蓋該月時，試算就會用你上傳的級距與費率**。只要在級距費率頁與試算結果交叉確認，即可判斷是否對應上。
