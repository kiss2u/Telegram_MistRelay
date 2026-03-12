import { getServerBaseUrl, normalizeServerBaseUrl, toAbsoluteServerUrl } from '@/utils/runtime'

export interface ConnectionCheckResult {
  ok: boolean
  serverBaseUrl: string
  statusCode?: number
  serverStatus?: string
  version?: string
  message: string
}

export async function checkServerConnection(serverBaseUrl?: string): Promise<ConnectionCheckResult> {
  const normalizedServerBaseUrl = normalizeServerBaseUrl(serverBaseUrl ?? getServerBaseUrl())
  const statusUrl = normalizedServerBaseUrl
    ? `${normalizedServerBaseUrl}/api/status`
    : toAbsoluteServerUrl('/api/status')

  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 8000)

  try {
    const response = await fetch(statusUrl, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: controller.signal,
    })

    const payload = await response.json().catch(() => null)

    if (!response.ok) {
      return {
        ok: false,
        serverBaseUrl: normalizedServerBaseUrl,
        statusCode: response.status,
        message: payload?.error || `服务返回 ${response.status}`,
      }
    }

    return {
      ok: true,
      serverBaseUrl: normalizedServerBaseUrl,
      statusCode: response.status,
      serverStatus: payload?.server_status,
      version: payload?.version,
      message: payload?.version
        ? `连接成功，服务器版本 ${payload.version}`
        : '连接成功',
    }
  } catch (error) {
    const message = error instanceof DOMException && error.name === 'AbortError'
      ? '连接超时，请检查服务器地址或网络'
      : '无法连接到服务器'

    return {
      ok: false,
      serverBaseUrl: normalizedServerBaseUrl,
      message,
    }
  } finally {
    window.clearTimeout(timeoutId)
  }
}
