import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the api module before importing the service
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '@/services/api'
import {
  listTenants,
  getTenant,
  createTenant,
  updateTenant,
  deleteTenant,
} from '@/services/tenant.service'
import type { TenantCreate, TenantRead } from '@/types/tenant'

const MOCK_TENANT: TenantRead = {
  id: '11111111-1111-1111-1111-111111111111',
  name: 'Test Firma s.r.o.',
  ico: '12345678',
  dic: '2012345678',
  ic_dph: 'SK2012345678',
  address_street: 'Hlavna 1',
  address_city: 'Bratislava',
  address_zip: '81101',
  address_country: 'SK',
  bank_iban: 'SK3112000000198742637541',
  bank_bic: 'SUBASKBX',
  schema_name: 'tenant_12345678',
  default_role: 'accountant',
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

describe('tenant.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listTenants calls GET with pagination params', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { items: [MOCK_TENANT], total: 1, skip: 0, limit: 20 },
    })

    const result = await listTenants({ skip: 0, limit: 20 })

    expect(api.get).toHaveBeenCalledWith('/api/v1/tenants', {
      params: { skip: 0, limit: 20 },
    })
    expect(result.items).toHaveLength(1)
    expect(result.total).toBe(1)
  })

  it('getTenant calls GET with id', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: MOCK_TENANT })

    const result = await getTenant(MOCK_TENANT.id)

    expect(api.get).toHaveBeenCalledWith(
      `/api/v1/tenants/${MOCK_TENANT.id}`,
    )
    expect(result.name).toBe('Test Firma s.r.o.')
  })

  it('createTenant calls POST', async () => {
    const payload: TenantCreate = {
      name: 'Nova Firma s.r.o.',
      ico: '87654321',
      dic: '2087654321',
      ic_dph: null,
      address_street: 'Nova 5',
      address_city: 'Kosice',
      address_zip: '04001',
      address_country: 'SK',
      bank_iban: 'SK3112000000198742637542',
      bank_bic: null,
      default_role: 'accountant',
      is_active: true,
    }
    vi.mocked(api.post).mockResolvedValue({
      data: { ...MOCK_TENANT, ...payload, id: '22222222-2222-2222-2222-222222222222' },
    })

    const result = await createTenant(payload)

    expect(api.post).toHaveBeenCalledWith('/api/v1/tenants', payload)
    expect(result.name).toBe('Nova Firma s.r.o.')
  })

  it('updateTenant calls PATCH (not PUT)', async () => {
    const update = { name: 'Updated Firma' }
    vi.mocked(api.patch).mockResolvedValue({
      data: { ...MOCK_TENANT, name: 'Updated Firma' },
    })

    const result = await updateTenant(MOCK_TENANT.id, update)

    expect(api.patch).toHaveBeenCalledWith(
      `/api/v1/tenants/${MOCK_TENANT.id}`,
      update,
    )
    expect(result.name).toBe('Updated Firma')
    // Verify PUT is NOT used
    expect(api.get).not.toHaveBeenCalled()
  })

  it('deleteTenant calls DELETE', async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined })

    await deleteTenant(MOCK_TENANT.id)

    expect(api.delete).toHaveBeenCalledWith(
      `/api/v1/tenants/${MOCK_TENANT.id}`,
    )
  })
})

describe('Tenant types', () => {
  it('TenantRead type has required fields', () => {
    const tenant: TenantRead = { ...MOCK_TENANT }
    expect(tenant.id).toBeDefined()
    expect(tenant.name).toBeDefined()
    expect(tenant.ico).toBeDefined()
    expect(tenant.address_street).toBeDefined()
    expect(tenant.bank_iban).toBeDefined()
    expect(tenant.schema_name).toBeDefined()
    expect(tenant.default_role).toBeDefined()
    expect(tenant.is_active).toBeDefined()
    expect(tenant.created_at).toBeDefined()
    expect(tenant.updated_at).toBeDefined()
  })

  it('dic and ic_dph can be null', () => {
    const tenant: TenantRead = { ...MOCK_TENANT, dic: null, ic_dph: null }
    expect(tenant.dic).toBeNull()
    expect(tenant.ic_dph).toBeNull()
  })

  it('bank_bic can be null', () => {
    const tenant: TenantRead = { ...MOCK_TENANT, bank_bic: null }
    expect(tenant.bank_bic).toBeNull()
  })
})
