export function validateUsername(value: string): string {
  if (value.length < 3 || value.length > 32) return '用户名需要 3–32 个字符'
  if (!/^[A-Za-z0-9_-]+$/.test(value)) return '用户名只能包含字母、数字、下划线或短横线'
  return ''
}

export function validatePassword(value: string): string {
  return value.length < 8 ? '密码至少需要 8 个字符' : ''
}
