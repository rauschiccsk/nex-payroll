import axios from 'axios'
import type { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { authStore } from '@/stores/auth.store'

// ── Constants ──────────────────────────────────────────────
const API_TIMEOUT_MS = 30_000
const MAX_RETRIES = 2
const RETRY_DELAY_MS = 1_000
const RETRYABLE_STATUS_CODES = [408, 429, 502, 503, 504]

// ── Base URL ────────────────────────────────────────────
// In dev mode, Vite proxy handles /api → http://localhost:9172
// In production (Docker/Nginx), relative URL works as Nginx proxies /api
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

// ── Custom Error Class ──────────────────────────────────
export class ApiError extends Error {
  status?: number
  detail?: string | Record<string, unknown>[]

  constructor(
    message: string,
    status?: number,
    detail?: string | Record<string, unknown>[],
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

// ── Axios Instance ──────────────────────────────────────
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// ── Request Interceptor — attach JWT token & tenant header ─
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { token, tenantId } = authStore.getState()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (tenantId && config.headers) {
      config.headers['X-Tenant'] = tenantId
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ── Retry Helper ────────────────────────────────────────
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function shouldRetry(error: AxiosError): boolean {
  // Retry on network errors (no response) or specific status codes
  if (!error.response) return true
  return RETRYABLE_STATUS_CODES.includes(error.response.status)
}

// ── Response Interceptor — handle 401, retries & errors ─
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<{ detail?: string | Record<string, unknown>[] }>) => {
    const config = error.config as InternalAxiosRequestConfig & { _retryCount?: number }

    // Retry logic for transient failures
    if (config && shouldRetry(error)) {
      config._retryCount = config._retryCount ?? 0
      if (config._retryCount < MAX_RETRIES) {
        config._retryCount += 1
        await delay(RETRY_DELAY_MS * config._retryCount)
        return api.request(config)
      }
    }

    // 401 — clear auth and redirect to login
    if (error.response?.status === 401) {
      authStore.getState().clear()
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }

    // Extract error message from FastAPI detail
    const detail = error.response?.data?.detail
    let message: string

    if (typeof detail === 'string') {
      message = detail
    } else if (Array.isArray(detail) && detail.length > 0) {
      // Pydantic validation error format: [{loc: [...], msg: "...", type: "..."}]
      message = detail
        .map((d: Record<string, unknown>) => {
          const loc = Array.isArray(d.loc) ? d.loc.slice(1).join(' → ') : ''
          const msg = typeof d.msg === 'string' ? d.msg : JSON.stringify(d)
          return loc ? `${loc}: ${msg}` : msg
        })
        .join('; ')
    } else {
      message = error.message ?? 'An unexpected error occurred'
    }

    return Promise.reject(new ApiError(message, error.response?.status, detail))
  },
)

// ── Download Helper ─────────────────────────────────────
/**
 * Download a file from the API as a Blob.
 * Triggers browser download with the given filename.
 */
export async function downloadFile(url: string, filename: string): Promise<void> {
  const response = await api.get<Blob>(url, { responseType: 'blob' })
  const blobUrl = window.URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(blobUrl)
}

export default api
