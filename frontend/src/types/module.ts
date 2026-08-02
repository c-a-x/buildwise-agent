export interface ModuleStatus {
  key: string
  name: string
  agent_name: string
  status: string
  description: string
  planned_inputs: string[]
  planned_outputs: string[]
  available_endpoints: string[]
}
