import { describe, it, expect, beforeEach } from 'vitest'
import { authStore } from '@/stores/auth.store'

describe('authStore', () => {
  beforeEach(() => {
    authStore.getState().clear()
  })

  it('starts with null token and tenantId', () => {
    const state = authStore.getState()
    expect(state.token).toBeNull()
    expect(state.tenantId).toBeNull()
  })

  it('setToken stores the token in memory', () => {
    authStore.getState().setToken('jwt-abc-123')
    expect(authStore.getState().token).toBe('jwt-abc-123')
  })

  it('setTenantId stores the tenant id', () => {
    authStore.getState().setTenantId('550e8400-e29b-41d4-a716-446655440000')
    expect(authStore.getState().tenantId).toBe('550e8400-e29b-41d4-a716-446655440000')
  })

  it('clear resets both token and tenantId', () => {
    authStore.getState().setToken('some-token')
    authStore.getState().setTenantId('some-tenant')
    authStore.getState().clear()

    const state = authStore.getState()
    expect(state.token).toBeNull()
    expect(state.tenantId).toBeNull()
  })
})
