import type { LocationQuery } from 'vue-router'

export function taskIdFromQuery(query: LocationQuery): string | null {
  const value = query.task
  if (typeof value === 'string' && value.trim()) return value
  if (Array.isArray(value) && typeof value[0] === 'string' && value[0].trim()) return value[0]
  return null
}
