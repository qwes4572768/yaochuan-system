export interface Dependent {
  id?: number
  employee_id?: number
  name: string
  birth_date?: string
  national_id?: string
  relation: string
  city?: string
  is_disabled: boolean
  disability_level?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

export interface Employee {
  id?: number
  name: string
  birth_date: string
  national_id: string
  reg_address: string
  live_address: string
  live_same_as_reg: boolean
  salary_type?: string
  salary_value?: number | string
  insured_salary_level?: number | string
  enroll_date?: string
  cancel_date?: string
  dependent_count: number
  pension_self_6?: boolean
  /** 登載身份：security=保全、property=物業、smith=史密斯、lixiang=立翔人力 */
  registration_type?: 'security' | 'property' | 'smith' | 'lixiang'
  /** 領薪方式：SECURITY_FIRST/APARTMENT_FIRST/SMITH_FIRST/CASH/OTHER_BANK */
  pay_method?: 'SECURITY_FIRST' | 'APARTMENT_FIRST' | 'SMITH_FIRST' | 'CASH' | 'OTHER_BANK'
  bank_code?: string
  branch_code?: string
  bank_account?: string
  property_pay_mode?: 'monthly' | 'hourly' | 'daily' | 'WEEKLY_2H' | 'MONTHLY_8H_HOLIDAY'
  security_pay_mode?: 'monthly' | 'hourly' | 'daily'
  smith_pay_mode?: 'monthly' | 'hourly' | 'daily'
  lixiang_pay_mode?: 'monthly' | 'hourly' | 'daily'
  weekly_amount?: number | string
  property_salary?: number | string
  safety_pdf_path?: string
  contract_84_1_pdf_path?: string
  notes?: string
  dependents?: Dependent[]
  created_at?: string
  updated_at?: string
}

export interface SalaryBracketItem {
  level: number
  low: number
  high: number
}

export interface DocumentInfo {
  id: number
  employee_id: number
  document_type: string
  file_name: string
  file_path: string
  file_size?: number
  uploaded_at: string
}

export interface HealthInsuranceDetailRow {
  name: string
  role: string
  rule_applied: string[]
  original_personal: number
  reduced_personal: number
}

export interface HealthInsuranceBreakdown {
  original_personal_total: number
  reduced_personal_total: number
  employer_total: number
  detail: HealthInsuranceDetailRow[]
}

export interface InsuranceEstimate {
  insured_salary_level: number
  labor_insurance: { name: string; employer: number; employee: number; total: number }
  health_insurance: { name: string; employer: number; employee: number; total: number }
  health_insurance_breakdown?: HealthInsuranceBreakdown | null
  occupational_accident: { name: string; employer: number; employee: number; total: number }
  labor_pension: { name: string; employer: number; employee: number; total: number }
  group_insurance: { name: string; employer: number; employee: number; total: number }
  /** 員工自提6%（勾選時才有） */
  pension_self_6?: { name: string; employer: number; employee: number; total: number } | null
  total_employer: number
  total_employee: number
  total: number
  dependent_count: number
  /** true 表示本結果來自 Excel 試算檔，公司/員工/合計以 Excel 為準 */
  from_excel?: boolean
  /** 當月加保天數（有依加退保日按比例計費時才有） */
  insured_days?: number
  /** 計費說明 */
  billing_note?: string
  /** 計算過程（項目與公式說明），Excel 試算時為空 */
  calculation_steps?: { item: string; detail: string }[]
  /** true 表示本結果來自級距表查表（權威資料） */
  from_bracket_table?: boolean
  /** 級距表來源：file_name, imported_at */
  bracket_source?: { file_name: string; imported_at: string }
}

export interface RateItemRead {
  id: number
  table_id: number
  level_name?: string
  salary_min: number
  salary_max: number
  insured_salary?: number
  employee_rate: number
  employer_rate: number
  gov_rate?: number
  fixed_amount_if_any?: number
}

export interface RateTableRead {
  id: number
  type: string
  version: string
  effective_from: string
  effective_to?: string
  total_rate?: number
  note?: string
  items: RateItemRead[]
}

// ---------- 案場管理 ----------
export const SITE_TYPE_OPTIONS = [
  { value: 'community', label: '社區' },
  { value: 'factory', label: '工廠' },
] as const

export const SERVICE_TYPE_OPTIONS = [
  '駐衛保全服務',
  '公寓大廈管理服務',
  '保全綜合服務',
] as const

export interface SiteListItem {
  id: number
  name: string
  address?: string
  site_type?: string
  service_types?: string
  contract_start?: string
  contract_end?: string
  monthly_fee_excl_tax?: number | string
  monthly_fee_incl_tax?: number | string
  invoice_due_day?: number
  payment_due_day?: number
  client_name?: string
  customer_name?: string
  days_to_expire?: number | null
  status?: 'normal' | 'expiring' | 'expired' | 'inactive'
  current_month_expected_amount?: number | string | null
  current_month_received?: boolean
  is_active?: boolean
  is_archived?: boolean
  created_at?: string
  updated_at?: string
}

export interface Site {
  id?: number
  name: string
  address: string
  contract_start: string
  contract_end?: string
  client_name?: string
  monthly_amount?: number | string
  payment_method?: string
  receivable_day?: number
  notes?: string
  daily_required_count?: number
  shift_hours?: number | string
  is_84_1?: boolean
  night_shift_allowance?: number | string
  bear_labor_insurance?: boolean
  bear_health_insurance?: boolean
  has_group_or_occupational?: boolean
  rebate_type?: string
  rebate_value?: number | string
  site_type?: string
  service_types?: string
  monthly_fee_excl_tax?: number | string
  tax_rate?: number | string
  monthly_fee_incl_tax?: number | string
  invoice_due_day?: number
  payment_due_day?: number
  remind_days?: number
  customer_name?: string
  customer_tax_id?: string
  customer_contact?: string
  customer_phone?: string
  customer_email?: string
  invoice_title?: string
  invoice_mail_address?: string
  invoice_receiver?: string
  is_active?: boolean
  deactivated_at?: string
  deactivated_reason?: string
  is_archived?: boolean
  archived_at?: string
  archived_reason?: string
  created_at?: string
  updated_at?: string
}

export interface SiteListResponse {
  items: SiteListItem[]
  total: number
  page: number
  page_size: number
}

// ---------- 案場回饋 site_rebates ----------
export interface SiteRebate {
  id: number
  site_id: number
  item_name: string
  is_completed: boolean
  completed_date?: string | null
  cost_amount?: number | string | null
  receipt_pdf_path?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface SiteRebateCreate {
  item_name: string
  is_completed?: boolean
  completed_date?: string | null
  cost_amount?: number | string | null
  notes?: string | null
}

// ---------- 案場每月入帳 site_monthly_receipts ----------
export interface SiteMonthlyReceipt {
  id: number
  site_id: number
  billing_month: string
  expected_amount?: number | string | null
  is_received: boolean
  received_date?: string | null
  received_amount?: number | string | null
  payment_method?: string | null
  proof_pdf_path?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface SiteMonthlyReceiptCreate {
  billing_month: string
  expected_amount?: number | string | null
  is_received?: boolean
  received_date?: string | null
  received_amount?: number | string | null
  payment_method?: string | null
  notes?: string | null
}

export interface SiteMonthlyReceiptBatchCreate {
  year: number
}

// ---------- 巡邏管理 ----------
export interface DeviceFingerprint {
  userAgent: string
  platform: string
  browser: string
  language: string
  screen: string
  timezone: string
  ip?: string | null
}

export interface PatrolBindingCode {
  code: string
  expires_at: string
  bind_url: string
  qr_value: string
}

export interface PatrolPermanentQr {
  device_public_id: string
  qr_url: string
  qr_value: string
  status: 'permanent'
}

export interface PatrolBindRequest {
  code: string
  employee_name: string
  password: string
  site_name: string
  device_fingerprint: DeviceFingerprint
}

export interface PatrolBindResponse {
  device_token: string
  employee_name: string
  site_name: string
  bound_at: string
}

export interface PatrolDeviceInfo {
  id: number
  employee_name: string
  site_name: string
  is_active: boolean
  password_set: boolean
  bound_at: string
  unbound_at?: string | null
  device_fingerprint?: string
}

export interface PatrolBindingStatus {
  is_bound: boolean
  employee_name?: string
  site_name?: string
  ua?: string
  platform?: string
  browser?: string
  language?: string
  screen?: string
  timezone?: string
  password_set: boolean
  bound_at?: string
}

export interface PatrolBoundLoginRequest {
  employee_name: string
  password: string
  device_fingerprint: DeviceFingerprint
}

export interface PatrolBoundLoginResponse {
  device_token: string
  employee_name: string
  site_name: string
  bound_at: string
}

export interface PatrolDeviceStatus {
  device_public_id: string
  is_bound: boolean
  employee_name?: string
  site_name?: string
  ua?: string
  platform?: string
  browser?: string
  language?: string
  screen?: string
  timezone?: string
  password_set: boolean
  bound_at?: string
}

export interface PatrolDeviceBindRequest {
  employee_name: string
  password: string
  site_name: string
  device_fingerprint: DeviceFingerprint
}

export interface PatrolDeviceStartRequest {
  employee_name: string
  password: string
  device_fingerprint: DeviceFingerprint
}

export interface PatrolUnbindRequest {
  employee_name: string
  password: string
  device_fingerprint: DeviceFingerprint
}

export interface PatrolUnbindResponse {
  success: boolean
  message: string
  unbound_at: string
}

export interface PatrolPoint {
  id: number
  public_id: string
  point_code: string
  point_name: string
  site_id?: number | null
  site_name?: string | null
  location?: string | null
  is_active: boolean
  qr_url: string
  created_at: string
  updated_at: string
}

export interface PatrolPointQr {
  public_id: string
  point_code: string
  qr_url: string
  qr_value: string
}

export interface PatrolCheckinResponse {
  id: number
  employee_id?: number | null
  employee_name: string
  site_name: string
  point_code: string
  point_name: string
  checkin_date: string
  checkin_time: string
  checkin_ampm: string
  created_at: string
}

export interface PatrolLog {
  id: number
  employee_name: string
  site_name: string
  point_code: string
  point_name: string
  checkin_date: string
  checkin_time: string
  checkin_ampm: string
  created_at: string
}
