const SERVER_BASE_URL_KEY = 'mistrelay.serverBaseUrl'
const TOKEN_KEY = 'token'

export function normalizeServerBaseUrl(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return ''

  const withProtocol = /^https?:\/\//i.test(trimmed) || trimmed.startsWith('/')
    ? trimmed
    : `https://${trimmed}`

  return withProtocol.replace(/\/+$/, '')
}

export function isDesktopShell(): boolean {
  return true
}

export function shouldUseHashHistory(): boolean {
  return true
}

export function getDefaultServerBaseUrl(): string {
  return normalizeServerBaseUrl(import.meta.env.VITE_SERVER_BASE_URL || '')
}

export function getServerBaseUrl(): string {
  const stored = localStorage.getItem(SERVER_BASE_URL_KEY)
  return normalizeServerBaseUrl(stored || getDefaultServerBaseUrl())
}

export function setServerBaseUrl(value: string): string {
  const normalized = normalizeServerBaseUrl(value)

  if (normalized) {
    localStorage.setItem(SERVER_BASE_URL_KEY, normalized)
  } else {
    localStorage.removeItem(SERVER_BASE_URL_KEY)
  }

  return normalized
}

export function isValidServerBaseUrl(value: string): boolean {
  const normalized = normalizeServerBaseUrl(value)

  if (!normalized) {
    return true
  }

  try {
    new URL(normalized, window.location.origin)
    return true
  } catch {
    return false
  }
}

export function getApiBaseUrl(): string {
  const serverBaseUrl = getServerBaseUrl()
  return serverBaseUrl ? `${serverBaseUrl}/api` : '/api'
}

export function resolveServerUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const serverBaseUrl = getServerBaseUrl()
  return serverBaseUrl ? `${serverBaseUrl}${normalizedPath}` : normalizedPath
}

export function toAbsoluteServerUrl(path: string): string {
  return new URL(resolveServerUrl(path), window.location.origin).toString()
}

export function getAuthToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setAuthToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearAuthToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function buildAuthorizedApiUrl(
  path: string,
  params: Record<string, string | number | boolean | null | undefined> = {},
): string {
  const url = new URL(toAbsoluteServerUrl(path))
  const token = getAuthToken()

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    url.searchParams.set(key, String(value))
  })

  if (token) {
    url.searchParams.set('token', token)
  }

  return url.toString()
}

export function getLoginRouteUrl(): string {
  return shouldUseHashHistory() ? '/#/login' : '/login'
}

export function redirectToLogin(): void {
  window.location.replace(getLoginRouteUrl())
}
