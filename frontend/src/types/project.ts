export interface Project {
  id: string
  code: string
  name: string
  address: string
  description: string
  status: string
  manager_user_id: string
}

export interface ProjectCreate {
  code: string
  name: string
  address: string
  description: string
}
