/**
 * 统一 HTTP 客户端（后续可换成 axios / fetch 封装）
 * 首版使用原生 fetch，保持轻量
 */
const BASE_URL = import.meta.env.VITE_API_BASE || '/api/v1'

export interface APIResponse<T = unknown> {
  success: boolean
  code: number
  message: string
  data: T | null
  timestamp: string
}

export async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<APIResponse<T>> {
  const url = path.startsWith('http') ? path : `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`)
  }
  return data as APIResponse<T>
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
