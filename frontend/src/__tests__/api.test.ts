import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock import.meta.env before importing api
vi.stubGlobal('window', {
  location: { pathname: '/', href: '' },
  URL: { createObjectURL: vi.fn(() => 'blob:mock-url'), revokeObjectURL: vi.fn() },
})

// Must import store before api (api imports store)
import { authStore } from '@/stores/auth.store'

type InterceptorHandler = {
  fulfilled: (config: Record<string, unknown>) => Record<string, unknown>
}

function getRequestInterceptor(api: { interceptors: { request: unknown } }): InterceptorHandler {
  return (api.interceptors.request as { handlers: InterceptorHandler[] }).handlers[0]!
}

function makeConfig(): { headers: Record<string, unknown>; url: string } {
  return {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    url: '/test',
  }
}

describe('api interceptors', () => {
  beforeEach(() => {
    authStore.getState().clear()
  })

  it('attaches Authorization header when token is set', async () => {
    const { default: api } = await import('@/services/api')

    authStore.getState().setToken('test-jwt-token')

    const interceptor = getRequestInterceptor(api)
    const result = interceptor.fulfilled(makeConfig()) as { headers: Record<string, unknown> }
    expect(result.headers['Authorization']).toBe('Bearer test-jwt-token')
  })

  it('attaches X-Tenant header when tenantId is set', async () => {
    const { default: api } = await import('@/services/api')

    authStore.getState().setTenantId('tenant-uuid-123')

    const interceptor = getRequestInterceptor(api)
    const result = interceptor.fulfilled(makeConfig()) as { headers: Record<string, unknown> }
    expect(result.headers['X-Tenant']).toBe('tenant-uuid-123')
  })

  it('does not attach headers when store is empty', async () => {
    const { default: api } = await import('@/services/api')

    const interceptor = getRequestInterceptor(api)
    const result = interceptor.fulfilled(makeConfig()) as { headers: Record<string, unknown> }
    expect(result.headers['Authorization']).toBeUndefined()
    expect(result.headers['X-Tenant']).toBeUndefined()
  })
})

describe('ApiError', () => {
  it('creates error with status and detail', async () => {
    const { ApiError } = await import('@/services/api')
    const err = new ApiError('Not found', 404, 'Entity not found')
    expect(err.message).toBe('Not found')
    expect(err.status).toBe(404)
    expect(err.detail).toBe('Entity not found')
    expect(err.name).toBe('ApiError')
    expect(err).toBeInstanceOf(Error)
  })

  it('creates error without optional fields', async () => {
    const { ApiError } = await import('@/services/api')
    const err = new ApiError('Network error')
    expect(err.message).toBe('Network error')
    expect(err.status).toBeUndefined()
    expect(err.detail).toBeUndefined()
  })
})

describe('api module exports', () => {
  it('exports default api instance', async () => {
    const { default: api } = await import('@/services/api')
    expect(api).toBeDefined()
    expect(api.defaults.timeout).toBe(30_000)
    expect(api.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('exports downloadFile function', async () => {
    const { downloadFile } = await import('@/services/api')
    expect(typeof downloadFile).toBe('function')
  })

  it('exports ApiError class', async () => {
    const { ApiError } = await import('@/services/api')
    expect(typeof ApiError).toBe('function')
  })
})
