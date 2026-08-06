export interface AuditLogEntry {
  id: string
  user_id: string
  username: string
  action: string
  resource_type: string
  resource_id: string | null
  detail_json: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
  limit: number
  offset: number
}
