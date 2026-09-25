/**
 * API 客户端
 */
const BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export interface APIResponse<T = unknown> {
  success: boolean
  code: number
  message: string
  data: T
  timestamp?: string
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith('http') ? path : `${BASE}${path}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })
  let json: any
  const text = await res.text()
  try {
    json = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(res.ok ? '响应非 JSON' : `HTTP ${res.status}: ${text.slice(0, 200)}`)
  }
  // FastAPI HTTPException detail
  if (!res.ok) {
    const detail = json.detail || json.message || json.error?.message
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ')
      : `HTTP ${res.status}`
    throw new Error(msg)
  }
  if (json.success === false) {
    throw new Error(json.message || '业务失败')
  }
  return (json.data !== undefined ? json.data : json) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

// ---- 类型 ----
export interface Material {
  id: number
  code: string
  name: string
  spec?: string
  material_type: string
  base_unit: string
  is_batch_managed: boolean
  is_roll_managed: boolean
  is_active: boolean
  remark?: string
}

export interface Supplier {
  id: number
  code: string
  name: string
  short_name?: string
  contact?: string
  phone?: string
  is_active: boolean
}

export interface Warehouse {
  id: number
  code: string
  name: string
  warehouse_type: string
  is_active: boolean
}

export interface StockBalance {
  id: number
  material_id: number
  warehouse_id: number
  location_id?: number
  batch_no: string
  roll_no: string
  qty: string | number
  qty_reserved: string | number
  qty_frozen: string | number
  available_qty: string | number
}

export interface StockLedger {
  id: number
  source_type: string
  source_id: string
  material_id: number
  warehouse_id: number
  batch_no: string
  qty: string | number
  unit: string
  direction: string
  is_reversed: boolean
  remark?: string
  created_at: string
}

export interface PurchaseOrder {
  id: number
  doc_no: string
  status: string
  supplier_id: number
  order_date: string
  expected_date?: string
  currency: string
  remark?: string
  lines: Array<{
    id: number
    line_no: number
    material_id: number
    qty: string | number
    qty_received: string | number
    unit: string
    unit_price?: string | number
  }>
}

export interface HealthData {
  status: string
  app_name: string
  version: string
  environment: string
  database: string
}
