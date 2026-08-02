import type { RiskLevel } from '@/types/api'

export const riskLabels: Record<RiskLevel, string> = {
  normal: '正常',
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  critical: '重大风险',
}

export const statusLabels: Record<string, string> = {
  pending: '待整改',
  in_progress: '整改中',
  pending_review: '待复查',
  closed: '已关闭',
  planned: '规划中',
  available: '已可用',
}

export function riskLabel(value: string): string {
  return riskLabels[value as RiskLevel] ?? value
}

export function statusLabel(value: string): string {
  return statusLabels[value] ?? value
}
