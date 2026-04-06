import axios from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { authStore } from '@/stores/auth.store'

// ── Constants ──────────────────────────────────────────────
const API_TIMEOUT_MS = 30_000

// ── Base URL ────────────────────────────────────────────
// In dev mode, Vite proxy handles /api → http://localhost:9172
// In production (Docker/Nginx), relative URL works as Nginx proxies /api
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

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

// ── Response Interceptor — handle 401 & errors ──────────
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response?.status === 401) {
      // Clear in-memory auth state and redirect to login
      authStore.getState().clear()
      // Only redirect if not already on login page
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }

    // Extract error message from FastAPI detail
    const detail = error.response?.data?.detail
    const message = detail ?? error.message ?? 'An unexpected error occurred'

    return Promise.reject(new Error(message))
  },
)

export default api
