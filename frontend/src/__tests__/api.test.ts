import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock import.meta.env before importing api
vi.stubGlobal('window', {
  location: { pathname: '/', href: '' },
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
