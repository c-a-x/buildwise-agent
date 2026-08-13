export interface HardwareTelemetry {
  device_id: string
  temperature_c: number
  humidity_pct: number
  heat_alarm: boolean
  buzzer_on: boolean
  led_state: string | null
  ip_address: string | null
  rssi_dbm: number | null
  uptime_ms: number | null
  note: string | null
  observed_at: string
  received_at: string
  is_fresh: boolean
}
