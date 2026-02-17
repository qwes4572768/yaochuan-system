export type RegistrationType = 'security' | 'property' | 'smith' | 'lixiang'

const LEGACY_LIXIANG_TYPO = '\u7acb\u7fd4\u4eba\u9ad4'
const LIXIANG_DISPLAY = '\u7acb\u7fd4\u4eba\u529b'

export function normalizeRegistrationLabel(label: string): string {
  return label === LEGACY_LIXIANG_TYPO ? LIXIANG_DISPLAY : label
}

export const REGISTRATION_OPTIONS: Array<{ key: RegistrationType; label: string }> = [
  { key: 'security', label: '保全' },
  { key: 'property', label: '物業' },
  { key: 'smith', label: '史密斯' },
  { key: 'lixiang', label: normalizeRegistrationLabel(LIXIANG_DISPLAY) },
]

export function registrationTypeLabel(type?: string): string {
  if (!type) return '保全'
  if (type === LEGACY_LIXIANG_TYPO || type === LIXIANG_DISPLAY) return LIXIANG_DISPLAY
  const item = REGISTRATION_OPTIONS.find((opt) => opt.key === type)
  return item?.label ?? '保全'
}
