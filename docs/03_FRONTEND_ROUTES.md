# 3) 前端頁面路由

## 路由表

| 路徑 | 元件 | 說明 |
|------|------|------|
| / | EmployeeList | 員工列表（搜尋姓名/身分證後四碼） |
| /employees/new | EmployeeForm | 新增員工 |
| /employees/:id | EmployeeDetail | 員工詳情（眷屬列表、當月試算、PDF 上傳/下載） |
| /employees/:id/edit | EmployeeForm | 編輯員工 |
| /reports | Reports | 報表匯出（選月份 → 公司負擔總表、員工個人負擔明細、眷屬明細、員工清單） |
| /rate-tables | RateTables | 級距費率管理（當月有效級距、匯入 JSON/Excel） |

## 導覽列

- 員工清單 → /
- 新增員工 → /employees/new
- 報表匯出 → /reports
- 級距費率 → /rate-tables

## 流程

1. **員工**：列表 → 檢視(詳情) / 編輯 / 新增；詳情內可管理眷屬、試算、上傳 PDF。
2. **眷屬**：在員工新增/編輯表單依「眷屬數量」顯示區塊，新增眷屬（最多 N 筆）；詳情頁顯示眷屬列表。
3. **試算**：詳情頁顯示當月試算；報表頁選月份可匯出公司負擔、個人負擔、眷屬明細。
4. **PDF**：詳情頁選擇類型（安全查核/84-1）後上傳；僅接受 application/pdf，單檔最大 10MB。
