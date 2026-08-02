const TOKEN_KEY = 'buildwise_access_token'
const PROJECT_KEY = 'buildwise_project_id'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string, remember = true): void {
  if (remember) {
    localStorage.setItem(TOKEN_KEY, token)
    sessionStorage.removeItem(TOKEN_KEY)
  } else {
    sessionStorage.setItem(TOKEN_KEY, token)
    localStorage.removeItem(TOKEN_KEY)
  }
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(TOKEN_KEY)
}

export function getProjectId(): string | null {
  return localStorage.getItem(PROJECT_KEY)
}

export function setProjectId(projectId: string): void {
  localStorage.setItem(PROJECT_KEY, projectId)
}
