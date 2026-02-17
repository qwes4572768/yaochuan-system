/** 敏感欄位 UI 遮罩：身分證、地址（列表/詳情顯示用） */

export function maskIdNumber(value: string | null | undefined): string {
  if (!value) return '－'
  if (value.includes('*')) return value
  if (value.length < 4) return '***'
  return value.slice(0, 2) + '****' + value.slice(-4)
}

export const maskNationalId = maskIdNumber

export function maskAddress(value: string | null | undefined): string {
  if (!value) return '－'
  if (value.includes('*')) return value
  if (value.length <= 6) return '***'
  return value.slice(0, 6) + '***'
}

